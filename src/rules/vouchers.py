import binascii
import logging
import uuid
import copy
import datetime
import sqlalchemy
from data import OrderData
from rule import Rule
from src.enums import VoucherTransactionStatus, VoucherType
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
        self.type = kwargs.get('type')
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.rules_list = kwargs.get('rules_list')
        self.custom = kwargs.get('custom')

    def get_rule(self, db=None):
        rule_id_list = self.rules.split(',')
        rules_list = list()
        for rule_id in rule_id_list:
            rule = Rule.find_one(rule_id, db=None)
            rules_list.append(rule)
        self.rules_list = rules_list
        return rules_list

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin()
        try:
            voucher_list = Vouchers.find_all_by_code(self.code)
            for voucher in voucher_list:
                if not self.can_coexist(voucher):
                    db.rollback()
                    return False
            db.insert_row("vouchers", **values)
            db.insert_row("all_vouchers", **values)
            db.commit()
        except sqlalchemy.exc.IntegrityError as e:
            db.rollback()
            return False
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False
        # else:
        #     db.commit()
        return {'id': self.id, 'code': self.code}

    def update_to_date(self, to_date):
        db = CouponsAlchemyDB()
        db.begin()
        try:
            now = datetime.datetime.utcnow()
            if self.to_date < now < to_date:
                # voucher has expired and I am setting date of future,
                # i.e. re-enabling the voucher
                # need to check if the freebie clashes with some existing.
                # Also update if the voucher already exists in voucher table
                # or auto_freebie_search table
                # else insert rows in both the tables while updating all_vouchers
                self.to_date = to_date
                if self.type is not VoucherType.regular_coupon.value:
                    self.get_rule(db)
                    existing_voucher_dict = {
                        'type': self.type,
                        'zone': self.rules_list[0].criteria_obj.zone[0],
                        'range_min': self.rules_list[0].criteria_obj.range_min,
                        'range_max': self.rules_list[0].criteria_obj.range_max,
                        'cart_range_min': self.rules_list[0].criteria_obj.cart_range_min,
                        'cart_range_max': self.rules_list[0].criteria_obj.cart_range_max,
                        'from': self.from_date,
                        'to': self.to_date,
                        'code': self.code
                    }
                    if self.type is VoucherType.auto_freebie.value:
                        existing_voucher_dict['variants'] = self.rules_list[0].criteria_obj.variants[0]
                    else:
                        existing_voucher_dict['variants'] = None
                    from src.rules.utils import find_overlapping_vouchers
                    success, error_list = find_overlapping_vouchers(existing_voucher_dict, db)
                    if not success:
                        db.rollback()
                        return False, error_list
                    # insert values in auto freebie table
                    # first cyclic import of the code!!!
                    auto_freebie_dict = db.find_one("auto_freebie_search", **{'voucher_id': self.id_bin})
                    if auto_freebie_dict:
                        db.update_row("auto_freebie_search", "voucher_id", voucher_id=self.id_bin, to_date=self.to_date)
                    else:
                        from utils import save_auto_freebie_from_voucher
                        save_auto_freebie_from_voucher(self, db)
                voucher_dict = db.find_one("vouchers", **{'id': self.id_bin})
                if voucher_dict:
                    db.update_row("vouchers", "id", id=self.id_bin, to=self.to_date)
                    db.update_row("all_vouchers", "id", id=self.id_bin, to=self.to_date)
                else:
                    value_dict = self.get_value_dict()
                    db.insert_row("vouchers", **value_dict)
                    db.update_row("all_vouchers", "id", id=self.id_bin, to=self.to_date)
            elif self.to_date > now and to_date > now:
                # voucher has not expired and the request is to extend the end date further
                # Hence just update all_vouchers and in case of freebies, update there as well
                self.to_date = to_date
                db.update_row("all_vouchers", "id", to=self.to_date, id=self.id_bin)
                db.update_row("vouchers", "id", to=self.to_date, id=self.id_bin)
                if self.type is not VoucherType.regular_coupon.value:
                    db.update_row("auto_freebie_search", "voucher_id", voucher_id=self.id_bin, to_date=self.to_date)
            elif to_date < now < self.to_date:
                # The voucher has not expired but request wants to expire the voucher
                # Go ahead delete rows from vouchers and auto_freebie_search
                # and update to=now in all_vouchers
                # expire request
                db.update_row("all_vouchers", "id", to=now, id=self.id_bin)
                self.delete(db)
            elif to_date < now and self.to_date < now:
                # Its a request to expire a voucher which has already expired.
                # go ahead and delete it if it exists in vouchers and auto_freebie_search table
                self.delete(db)
            else:
                # Unknown case has not been handled, Hence putting a logger
                logger.error(u'The Voucher : {}, to_date: {}'.format(self.__dict__, to_date))
            db.commit()
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False, [u'Unknown Error, Please try again after some time']
        # else:
        #     db.commit()
        return True, None

    def get_value_dict(self):
        values = dict()
        values['id'] = self.id_bin
        values['code'] = self.code
        values['rules'] = self.rules
        values['description'] = self.description
        values['from'] = self.from_date
        values['to'] = self.to_date
        values['type'] = self.type
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
    def find_one_all_vouchers(code):
        db = CouponsAlchemyDB()
        voucher_dict = db.find("all_vouchers", order_by="_to", _limit=1, **{'code': code})
        if voucher_dict:
            voucher_dict = voucher_dict[0]
            voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
            voucher = Vouchers(**voucher_dict)
            return voucher
        return False

    @staticmethod
    def find_all_by_code(code):
        db = CouponsAlchemyDB()
        voucher_list = list()
        voucher_dict_list = db.find("all_vouchers", **{'code': code})
        for voucher_dict in voucher_dict_list:
            voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
            voucher = Vouchers(**voucher_dict)
            voucher_list.append(voucher)
        return voucher_list

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
        rules = self.get_rule()
        if not self.is_coupon_valid_with_existing_coupon(order):
            failed_dict = {
                'voucher': self,
                'error': u'This coupon {} is not valid with other coupons'.format(self.code)
            }
            order.failed_vouchers.append(failed_dict)
            return

        voucher_match = False
        failed_rule_list = list()
        for rule in rules:
            status = rule.check_usage(order.customer_id, self.id_bin)
            if not status.get('success', False):
                failed_voucher = copy.deepcopy(self)
                failed_voucher.rules_list = [rule]
                failed_dict = {
                    'voucher': failed_voucher,
                    'error': u'Voucher {} has expired'.format(self.code)
                }
                failed_rule_list.append(failed_dict)
                # continue
                break
            success, data, error = rule.match(order, self.code)
            if not success:
                failed_voucher = copy.deepcopy(self)
                failed_voucher.rules_list = [rule]
                failed_dict = {
                    'voucher': failed_voucher,
                    'error': error
                }
                failed_rule_list.append(failed_dict)
                continue
            effectiveVoucher = copy.deepcopy(self)
            effectiveVoucher.rules_list = [rule]
            success_dict = {
                'voucher': effectiveVoucher,
                'total': data.get('total'),
                'subscription_id_list': data.get('subscription_id_list')
            }
            order.existing_vouchers.append(success_dict)
            voucher_match = True
        if not voucher_match:
            error_msg = ''
            for index, failed_rule in enumerate(failed_rule_list):
                if index is 0:
                    error_msg = failed_rule['error']
                else:
                    if not error_msg.startswith('No matching items'):
                        error_msg += ' or ' + failed_rule['error']

            failed_dict = {
                'voucher': self,
                'error': error_msg
            }
            order.failed_vouchers.append(failed_dict)
# removed below check because we can have any number of auto-applied vouchers. TODO: it would be better if we can still have such preemptive check for regular vouchers beyond a threshold like 1 or 2
#        if len(order.existing_vouchers) == 2:
#            order.can_accommodate_new_vouchers = False

    def is_coupon_valid_with_existing_coupon(self, order):
        success = True
        single_voucher_types_list = [VoucherType.regular_coupon, VoucherType.regular_freebie]
        if self.type in single_voucher_types_list:
            for existing_voucher in order.existing_vouchers:
                if existing_voucher['voucher'].type in single_voucher_types_list:
                    success = False
                    break
        return success

    def can_coexist(self, voucher):
        assert isinstance(voucher, Vouchers)
        # if self.type is VoucherType.regular_coupon.value or voucher.type is VoucherType.regular_coupon.value:
        #     return False
        now = datetime.datetime.utcnow()
        if voucher.to_date > now:
            return False
        return True

    def delete(self, db=None):
        if not db:
            db = CouponsAlchemyDB()
        db.delete_row_in_transaction("vouchers", **{'id': self.id_bin})
        if self.type is not VoucherType.regular_coupon.value:
            db.delete_row_in_transaction("auto_freebie_search", **{'voucher_id': self.id_bin})

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
        self.response = kwargs.get('response')

    def save(self, db=None):
        values = self.get_value_dict_for_log()
        if not db:
            db = CouponsAlchemyDB()
            db.begin()
            try:
                function = self.save_function().get(self.status_enum)
                function(db, values)
                db.commit()
            except Exception as e:
                logger.exception(e)
                db.rollback()
                return False
            # else:
            #     db.commit()
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
        values['response'] = self.response
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
            db.commit()
        except Exception as e:
            logger.exception(e)
            db.rollback()
            success = False
            error = u'Unknown error'
        # else:
        #     db.commit()

        return success, error
