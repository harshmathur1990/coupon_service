import binascii
import logging
import uuid

import sqlalchemy
from data import OrderData
from rule import Rule
from src.enums import VoucherTransactionStatus, RuleType
from src.sqlalchemydb import CouponsAlchemyDB

logger = logging.getLogger()


class Vouchers(object):
    def __init__(self, **kwargs):
        # instantiate this class with a helper function
        id = kwargs.get('id')  # id should be uuid.uuid1().hex
        self.id = id
        if self.id:
            self.id_bin = binascii.a2b_hex(self.id)
        self.rules = kwargs.get('rules')
        self.code = kwargs.get('code')
        self.description = kwargs.get('description')
        self.from_date = kwargs.get('from')
        self.to_date = kwargs.get('to')
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.rules_list = kwargs.get('rules_list')
        self.custom = kwargs.get('custom')

    def get_rule(self):
        rule_id_list = self.rules.split(',')
        rules_list = list()
        for rule_id in rule_id_list:
            rule = Rule.find_one(rule_id)
            rules_list.append(rule)
        self.rules_list = rules_list
        return rules_list

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin()
        try:
            db.insert_row("vouchers", **values)
            db.insert_row("all_vouchers", **values)
        except sqlalchemy.exc.IntegrityError as e:
            db.rollback()
            return False
        except Exception as e:
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
        values['rules'] = self.rules
        values['description'] = self.description
        values['from'] = self.from_date
        values['to'] = self.to_date
        if self.created_by:
            values['created_by'] = self.created_by
        values['updated_by'] = self.updated_by
        values['custom'] = self.custom
        return values

    @staticmethod
    def find_one(code):
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': code})
        if voucher_dict:
            voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
            voucher = Vouchers(**voucher_dict)
            return voucher
        return False

    @staticmethod
    def find_one_by_id(id):
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'id': id})
        if voucher_dict:
            voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
            voucher = Vouchers(**voucher_dict)
            return voucher
        return False

    def match(self, order):
        assert isinstance(order, OrderData)
        rule = self.get_rule()
        if not self.is_coupon_valid_with_existing_coupon(order):
            failed_dict = {
                'voucher': self,
                'error': u'This coupon is not valid with other coupons'
            }
            order.failed_vouchers.append(failed_dict)
            return

        status = rule.check_usage(order.customer_id, self.id)
        if not status.get('success', False):
            failed_dict = {
                'voucher': self,
                'error': status.get('msg')
            }
            order.failed_vouchers.append(failed_dict)
            return
        success, data, error = rule.match(order)
        if not success:
            failed_dict = {
                'voucher': self,
                'error': error
            }
            order.failed_vouchers.append(failed_dict)
            return
        success_dict = {
            'voucher': self,
            'total': data.get('total'),
            'subscription_id_list': data.get('subscription_id_list')
        }
        order.existing_vouchers.append(success_dict)
        if len(order.existing_vouchers) == 2:
            order.can_accomodate_new_vouchers = True

    def is_coupon_valid_with_existing_coupon(self, order):
        success = True

        for existing_voucher in order.existing_vouchers:
            if existing_voucher['voucher'].rule.rule_type == self.rule.rule_type:
                success = False
                break
        return success

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

    def save(self, db=None):
        values = self.get_value_dict_for_log()
        if not db:
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
        else:
            function = self.save_function().get(self.status_enum)
            function(db, values)

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

    @staticmethod
    def dict_to_obj(data_dict):
        data_dict['voucher_id'] = binascii.b2a_hex(data_dict['voucher_id'])
        data_dict['id'] = binascii.b2a_hex(data_dict['id'])
        return VoucherTransactionLog(**data_dict)

    @staticmethod
    def make_transaction_log_entry(args):
        db = CouponsAlchemyDB()
        db.begin()
        success = True
        error = None
        try:
            voucher_use_list_of_dict = db.find(
                "user_voucher_transaction_log", order_by="_updated_on",
                **{'order_id': args.get('order_id')})
            if not voucher_use_list_of_dict:
                success = False
                error = u'No Order found for the given order id'
            else:
                last_log = VoucherTransactionLog.dict_to_obj(voucher_use_list_of_dict[0])
                if last_log.status_enum is VoucherTransactionStatus.in_progress:
                    if args.get('payment_status'):
                        status = VoucherTransactionStatus.success.value
                    else:
                        status = VoucherTransactionStatus.failure.value
                    id = uuid.uuid1().hex
                    log = VoucherTransactionLog(**{
                        'id': id,
                        'user_id': last_log.user_id,
                        'voucher_id': last_log.voucher_id,
                        'order_id': last_log.order_id,
                        'status': status
                    })
                    log.save(db)
                    success = True
                    error = None
                else:
                    success = False
                    error = u'No Order in progress for the the given order id'
        except Exception as e:
            logger.exception(e)
            db.rollback()
            success = False
            error = u'Unknown error'
        else:
            db.commit()

        return success, error
