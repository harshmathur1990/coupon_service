import logging
from constants import VOUCHERS_KEY
import binascii
from src.sqlalchemydb import CouponsAlchemyDB
from src.enums import VoucherTransactionStatus
from rule import Rule
from lib import cache
logger = logging.getLogger()


class Vouchers(object):
    def __init__(self, **kwargs):
        # instantiate this class with a helper function
        id = kwargs.get('id')  # id should be uuid.uuid1().hex
        self.id = id
        if self.id:
            self.id_bin = binascii.a2b_hex(self.id)
        self.rule_id = kwargs.get('rule_id')
        if self.rule_id:
            self.rule_id_bin = binascii.a2b_hex(self.rule_id)
        self.code = kwargs.get('code')
        self.description = kwargs.get('description')
        self.from_date = kwargs.get('from')
        self.to_date = kwargs.get('to')
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.rule = kwargs.get('rule')

    def get_rule(self):
        if not self.rule:
            self.rule = Rule.find_one(self.rule_id)
        return self.rule

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin()
        try:
            db.insert_row("vouchers", **values)
            db.insert_row("all_vouchers", **values)
        except Exception as e:
            # TODO Exception handling for primary key dedup
            logger.exception(e)
            db.rollback()
            return False
        else:
            db.commit()
        return {'id': self.id, 'code': self.code}

    def get_value_dict(self):
        values = dict()
        values['id'] = self.id_bin
        values['code'] = self.code
        values['rule_id'] = self.rule_id_bin
        values['description'] = self.description
        values['from'] = self.from_date
        values['to'] = self.to_date
        if self.created_by:
            values['created_by'] = self.created_by
        values['updated_by'] = self.updated_by
        return values

    @staticmethod
    def find_one(code):
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': code})
        if voucher_dict:
            voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
            voucher_dict['rule_id'] = binascii.b2a_hex(voucher_dict['rule_id'])
            voucher = Vouchers(**voucher_dict)
            return voucher
        return False

    # def update_cache(self):
    #     voucher = Vouchers.find_one(self.id)
    #     voucher_key = VOUCHERS_KEY + self.code
    #     cache.set(voucher_key, voucher)


class VoucherTransactionLog(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')  # uuid.uuid1().hex
        if self.id:
            self.id_bin = binascii.a2b_hex(self.id)
        self.user_id = kwargs.get('user_id')
        self.voucher_id = kwargs.get('voucher_id')  # uuid.uuid1().hex
        if self.voucher_id:
            self.voucher_id_bin = binascii.a2b_hex(self.voucher_id)
        self.order_id = kwargs.get('order_id')
        self.status = kwargs.get('status')
        if self.status in [l.value for l in list(VoucherTransactionStatus)]:
            self.status_enum = VoucherTransactionStatus(self.status)

    def save(self):
        values = self.get_value_dict_for_log()
        db = CouponsAlchemyDB()
        db.begin()
        try:
            function = self.save_function().get(self.status_enum)
            function(db, values)
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False
        else:
            db.commit()
        return True

    def get_value_dict_for_log(self):
        values = dict()
        values['id'] = self.id_bin
        values['user_id'] = self.user_id
        values['voucher_id'] = self.voucher_id_bin
        values['order_id'] = self.order_id
        values['status'] = self.status
        return values

    def make_in_progress_entry(self, db, values):
        db.insert_row("user_voucher_transaction_log", **values)
        del values['status']
        db.insert_row("voucher_use_tracker", **values)

    def make_success_entry(self, db, values):
        db.insert_row("user_voucher_transaction_log", **values)

    def make_failure_entry(self, db, values):
        db.insert_row("user_voucher_transaction_log", **values)
        db.delete_row_in_transaction("voucher_use_tracker", **{'order_id': self.order_id})

    def save_function(self):
        return {
            VoucherTransactionStatus.in_progress: self.make_in_progress_entry,
            VoucherTransactionStatus.success: self.make_success_entry,
            VoucherTransactionStatus.failure: self.make_failure_entry
        }