import logging
import canonicaljson
import hashlib
import binascii
from src.sqlalchemydb import CouponsAlchemyDB
from rule import Rule
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
            voucher = Vouchers(**voucher_dict)
            return voucher
        return False
