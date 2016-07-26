import binascii
import copy
import datetime
import json
import logging
import importlib
import uuid
import sqlalchemy
from rule import Rule
from src.enums import VoucherTransactionStatus, VoucherType
from src.sqlalchemydb import CouponsAlchemyDB
from config import method_dict


logger = logging.getLogger(__name__)


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
        self.is_active = kwargs.get('is_active', True)
        self.schedule = kwargs.get('schedule')
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
            rule = Rule.find_one(rule_id, db)
            rules_list.append(rule)
        self.rules_list = rules_list
        return rules_list

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin()
        try:
            from src.rules.utils import is_validity_period_exclusive_for_voucher_code
            success, error = is_validity_period_exclusive_for_voucher_code(self, db)
            if not success:
                db.rollback()
                return False, None, error
            db.insert_row("all_vouchers", **values)
            Vouchers.fetch_active_voucher(self.code, db)
            db.commit()
        except sqlalchemy.exc.IntegrityError as e:
            db.rollback()
            # should not happen
            return False, None, u'Voucher code already exists'
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False, None, u'Unknown Error'
        # else:
        #     db.commit()
        return True, {'id': self.id, 'code': self.code}, None

    @staticmethod
    def get_active_voucher(code, db):
        now = datetime.datetime.now()
        active_voucher_params = {
            'to': now,
            'code': code
        }
        sql = "select * from all_vouchers where `to` >= :to && code=:code && is_active=1 order by `from` asc limit 0,1"
        active_voucher_dict = db.execute_raw_sql(sql, active_voucher_params)
        if active_voucher_dict:
            active_voucher = Vouchers.from_dict(active_voucher_dict[0])
            present_voucher = Vouchers.find_one(code, db)
            values = active_voucher.get_value_dict()
            del values['is_active']
            if not present_voucher:
                db.insert_row("vouchers", **values)
            else:
                if present_voucher.id != active_voucher.id:
                    db.delete_row_in_transaction("vouchers", **{'code': code})
                    db.insert_row("vouchers", **values)
            return active_voucher
        else:
            db.delete_row_in_transaction("vouchers", **{'code': code})
        return False

    @staticmethod
    def fetch_active_voucher(code, db=None):
        if not db:
            db = CouponsAlchemyDB()
            db.begin()
            try:
                active_voucher = Vouchers.get_active_voucher(code, db)
                db.commit()
                return active_voucher
            except Exception as e:
                logger.exception(e)
                db.rollback()
                return False
        else:
            return Vouchers.get_active_voucher(code, db)

    def update_to_date_single(self, to_date, db, force=False):
        validity_period_exclusive_for_benefit_voucher_callback = getattr(
            importlib.import_module(
                method_dict.get('check_auto_benefit_exclusivity')['package']),
            method_dict.get('check_auto_benefit_exclusivity')['attribute'])
        save_auto_benefits_from_voucher = getattr(
            importlib.import_module(
                method_dict.get(
                    'save_auto_benefits_from_voucher')['package']),
            method_dict.get('save_auto_benefits_from_voucher')['attribute'])
        now = datetime.datetime.utcnow()
        if self.to_date < now < to_date:
            # voucher has expired and I am setting date of future,
            # i.e. re-enabling the voucher
            # need to check if the freebie clashes with some existing.
            # Also update if the voucher already exists in voucher table
            # or auto_benefits table
            # else insert rows in both the tables while updating all_vouchers
            self.to_date = to_date
            if self.is_auto_benefit_voucher():
                success, error_list = validity_period_exclusive_for_benefit_voucher_callback(self, db)
                if not success:
                    return False, error_list
                # insert values in auto freebie table
                # first cyclic import of the code!!!
                auto_freebie_dict = db.find_one("auto_benefits", **{'voucher_id': self.id_bin})
                if auto_freebie_dict:
                    db.update_row("auto_benefits", "voucher_id", voucher_id=self.id_bin, to_date=self.to_date)
                else:
                    save_auto_benefits_from_voucher(self, db)
            voucher_dict = db.find_one("vouchers", **{'id': self.id_bin})
            if voucher_dict:
                db.update_row("vouchers", "id", id=self.id_bin, to=self.to_date)
                db.update_row("all_vouchers", "id", id=self.id_bin, to=self.to_date)
            else:
                db.update_row("all_vouchers", "id", id=self.id_bin, to=self.to_date)
            Vouchers.fetch_active_voucher(self.code, db)
        elif self.to_date > now and to_date > now:
            # voucher has not expired and the request is to extend the end date further
            # Hence just update all_vouchers and in case of freebies, update there as well
            self.to_date = to_date
            if self.is_auto_benefit_voucher():
                success, error_list = validity_period_exclusive_for_benefit_voucher_callback(self, db)
                if not success:
                    return False, error_list
            db.update_row("all_vouchers", "id", to=self.to_date, id=self.id_bin)
            db.update_row("vouchers", "id", to=self.to_date, id=self.id_bin)
            if self.type is not VoucherType.regular_coupon.value:
                db.update_row("auto_benefits", "voucher_id", voucher_id=self.id_bin, to_date=self.to_date)
            Vouchers.fetch_active_voucher(self.code, db)
        elif to_date < now < self.to_date:
            # The voucher has not expired but request wants to expire the voucher
            # Go ahead delete rows from vouchers and auto_benefits
            # and update to=now in all_vouchers
            # expire request
            self.delete(db)
            if self.from_date > now:
                db.delete_row_in_transaction("all_vouchers", **{'id': self.id_bin})
            else:
                if force:
                    self.to_date = to_date
                    db.update_row("all_vouchers", "id", to=self.to_date, id=self.id_bin)
                else:
                    db.update_row("all_vouchers", "id", to=now, id=self.id_bin)
            Vouchers.fetch_active_voucher(self.code, db)
        elif to_date < now and self.to_date < now:
            # Its a request to expire a voucher which has already expired.
            # go ahead and delete it if it exists in vouchers and auto_benefits table
            if force:
                self.to_date = to_date
                db.update_row("all_vouchers", "id", to=self.to_date, id=self.id_bin)
            self.delete(db)
            Vouchers.fetch_active_voucher(self.code, db)
        else:
            # Unknown case has not been handled, Hence putting a logger
            logger.error(u'The Voucher : {}, to_date: {}'.format(self.__dict__, to_date))
            return False, [u'Unknown Error, Please contact tech support']
        return True, None

    def update_to_date(self, to_date, db, force=False):
        now = datetime.datetime.now()
        if now < to_date <= self.from_date:
            return False, [u'to date cannot be less than from date']
        query_dict = {
            'to': self.to_date,
            'code': self.code,
            'from': self.from_date
        }
        sql = "select * from all_vouchers where `from` > :to && code=:code && `from` <> :from order by `from` asc limit 0,1"
        existing_voucher = db.execute_raw_sql(sql, query_dict)
        if existing_voucher:
            existing_voucher = Vouchers.from_dict(existing_voucher[0])
            if existing_voucher.from_date < now:
                # There is at least one voucher which follows chronologically, hence this voucher is locked.
                return False, [u'This voucher can not be extended, try creating a new voucher with same voucher code.']
            if to_date >= existing_voucher.from_date:
                # overlapping intervals
                return False, [u'Voucher to_date clashes with another voucher with same code']
        return self.update_to_date_single(to_date, db, force)

    def update(self, update_dict, db, change_id):

        new_update_dict = copy.deepcopy(update_dict)

        force = new_update_dict.pop('force', False)

        value_dict = self.get_value_dict()

        for key, items in update_dict.items():
            if key != 'force' and new_update_dict[key] == value_dict[key]:
                del new_update_dict[key]

        if not new_update_dict:
            return True, None

        new_update_dict['id'] = self.id_bin

        if 'to' in new_update_dict:
            success, error_list = self.update_to_date(new_update_dict.get('to'), db, force)
            if not success:
                return False, error_list
            del new_update_dict['to']

        db.update_row("all_vouchers", "id", **new_update_dict)
        if 'is_active' in new_update_dict:
            Vouchers.fetch_active_voucher(self.code, db)
            del new_update_dict['is_active']

        db.update_row("vouchers", "id", **new_update_dict)

        self.add_audit_log_entry(change_id, db)

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
        values['created_by'] = self.created_by
        values['updated_by'] = self.updated_by
        values['custom'] = self.custom
        values['is_active'] = self.is_active
        values['schedule'] = json.dumps(self.schedule)

        return values

    # def update_object(self, update_dict):
    #     if 'schedule' in update_dict:
    #         self.schedule = update_dict['schedule']
    #     if 'custom' in update_dict:
    #         self.custom = update_dict['custom']
    #     if 'description' in update_dict:
    #         self.description = update_dict['description']
    #     if 'to' in update_dict:
    #         self.to_date = update_dict['to']
    #     if 'is_active' in update_dict:
    #         self.is_active = update_dict['is_active']

    def add_audit_log_entry(self, change_id, db):
        # This method will get from db and update in audit trail.
        voucher = Vouchers.find_one_all_vouchers(self.code, self.from_date, db)
        now = datetime.datetime.utcnow()
        if not voucher:
            assert self.from_date >= now, u'Voucher {} with id {} has from date less than now'.format(self.code, self.id)
            return
        values = voucher.get_value_dict()
        values['change_id'] = change_id
        values['created_at'] = voucher.created_at
        values['updated_at'] = voucher.updated_at
        values['created_by'] = voucher.created_by
        values['updated_by'] = voucher.updated_by
        db.insert_row("all_vouchers_log", **values)

    @staticmethod
    def find_one(code, db=None):
        if not db:
            db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': code})
        if voucher_dict:
            voucher = Vouchers.from_dict(voucher_dict)
            return voucher
        return False

    @staticmethod
    def find_voucher_at_the_date(code, date, db=None):
        if not db:
            db = CouponsAlchemyDB()
        query = 'select * from all_vouchers where code=:code and `from` <= :date and `to >= :date`'
        args = {
            'code': code,
            'date': date
        }
        voucher_dict = db.execute_raw_sql(query, args)
        if voucher_dict:
            voucher = Vouchers.from_dict(voucher_dict[0])
            return voucher
        return False

    @staticmethod
    def find_one_all_vouchers(code, from_date, db=None):
        # from_date must be a timezone unaware UTC datetime object
        if not db:
            db = CouponsAlchemyDB()
        voucher_dict = db.find_one("all_vouchers", **{'code': code, 'from': from_date})
        if voucher_dict:
            voucher = Vouchers.from_dict(voucher_dict)
            return voucher
        return False

    @staticmethod
    def find_all_by_code(code, db=None):
        if not db:
            db = CouponsAlchemyDB()
        voucher_list = list()
        voucher_dict_list = db.find("all_vouchers", **{'code': code})
        for voucher_dict in voucher_dict_list:
            voucher = Vouchers.from_dict(voucher_dict)
            voucher_list.append(voucher)
        return voucher_list

    @staticmethod
    def find_one_by_id(id):
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'id': id})
        if voucher_dict:
            voucher = Vouchers.from_dict(voucher_dict)
            return voucher
        return False

    def match(self, order):
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
            success, data, error = rule.match(order, self)
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
                'item_id_list': data.get('item_id_list')
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
        if self.from_date <= voucher.to_date <= self.to_date \
                or self.from_date <= voucher.from_date <= self.to_date \
                or voucher.from_date <= self.from_date <= voucher.to_date \
                or voucher.from_date <= self.to_date <= voucher.to_date:
            return False
        return True

    def delete(self, db=None):
        if not db:
            db = CouponsAlchemyDB()
        db.delete_row_in_transaction("vouchers", **{'id': self.id_bin})
        if self.type is not VoucherType.regular_coupon.value:
            db.delete_row_in_transaction("auto_benefits", **{'voucher_id': self.id_bin})

    @staticmethod
    def from_dict(voucher_dict):
        voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
        if voucher_dict.get('schedule'):
            voucher_dict['schedule'] = json.loads(voucher_dict.get('schedule'))
        else:
            voucher_dict['schedule'] = list()
        voucher = Vouchers(**voucher_dict)
        return voucher

    def is_auto_benefit_voucher(self):
        if self.type is VoucherType.auto_freebie.value or self.type is VoucherType.regular_freebie.value:
            return True
        return False


class VoucherTransactionLog(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')  # uuid.uuid1().hex
        if self.id:
            self.id_bin = binascii.a2b_hex(self.id)
        self.user_id = kwargs.get('user_id')
        self.session_id = kwargs.get('session_id')
        self.user_uuid = kwargs.get('user_uuid')
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
        values['session_id'] = self.session_id
        values['user_uuid'] = self.user_uuid
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

        return success, error
