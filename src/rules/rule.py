import logging
import canonicaljson
import hashlib
import binascii
from src.enums import UseType, BenefitType
from src.sqlalchemydb import CouponsAlchemyDB
from lib import cache
from constants import RULE_CACHE_KEY
logger = logging.getLogger()


class Rule(object):

    def __init__(self, **kwargs):
        # instantiate this class with a helper function
        id = kwargs.get('id')  # id should be uuid.uuid1().hex
        self.id = id
        if self.id:
            self.id_bin = binascii.a2b_hex(self.id)
        self.name = kwargs.get('name')
        self.description = kwargs.get('description')
        self.rule_type = kwargs.get('rule_type')
        self.criteria_obj = kwargs.get('criteria_obj')
        self.criteria_json = kwargs.get('criteria_json')
        self.benefits_json = kwargs.get('benefits_json')
        self.benefits_obj = kwargs.get('benefits_obj')
        self.sha2hash = kwargs.get('sha2hash')
        self.active = kwargs.get('active', True)
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        if not self.rule_type:
            self.get_rule_type()
        if not self.criteria_obj:
            criteria_dict = canonicaljson.json.loads(self.criteria_json)
            self.criteria_obj = RuleCriteria(**criteria_dict)
        if not self.benefits_obj:
            benefits_dict = canonicaljson.json.loads(self.benefits_json)
            self.benefits_obj = Benefits(**benefits_dict)

    def get_rule_type(self):
        self.rule_type = 0
        pass

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin() # TODO db transaction should start outside of Rule class. We might want Rule creation and voucher creation as part of single transaction
        # update_cache = False
        try:
            # check if the rule being created already exists, if yes, just return rule id
            existing_rule = db.find_one("rule", **{'id': self.id_bin})
            if not existing_rule:
                # no existing rule exists for this id, now check if a rule exists for given attributes
                rule_list = db.find("rule", **{'sha2hash': values.get('sha2hash')})
                if rule_list:
                    for rule in rule_list:
                        rule['id'] = binascii.b2a_hex(rule['id'])
                        rule_obj = Rule(**rule)
                        if self == rule_obj:
                            self.id = rule_obj.id
                            break
                else:
                    # update_cache = True
                    db.insert_row("rule", **values)
            else:
                # call is to update the existing rule with new attributes, just update and save it
                # update_cache = True
                logger.error('Trying to update an existing rule {}'.format(self.__dict__))
                assert False, "A Rule is immutable."
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False
        else:
            db.commit()
        # if update_cache:
        #     self.update_cache()
        return self.id

    def get_value_dict(self):
        values = dict()
        values['id'] = self.id_bin
        if self.name:
            values['name'] = self.name
        if self.description:
            values['description'] = self.description
        values['rule_type'] = self.rule_type
        values['criteria_json'] = self.criteria_json
        values['benefits_json'] = self.benefits_json
        un_hashed_string = unicode(self.criteria_json) + \
                          unicode(self.benefits_json)
        values['sha2hash'] = hashlib.sha256(un_hashed_string).hexdigest()
        values['active'] = self.active
        if self.created_by:
            values['created_by'] = self.created_by
        values['updated_by'] = self.updated_by
        return values

    def __eq__(self, other):
        if self.criteria_obj == other.criteria_obj and \
                self.benefits_obj == other.benefits_obj:
            return True
        return False

    @staticmethod
    def find_one(id):
        id = binascii.a2b_hex(id)
        db = CouponsAlchemyDB()
        rule_dict = db.find_one("rule", **{'id': id})
        if rule_dict:
            rule_dict['id'] = binascii.b2a_hex(rule_dict['id'])
            rule = Rule(**rule_dict)
            return rule
        return False

    def check_usage(self, user_id, voucher_id):
        use_type = self.criteria_obj.usage['use_type']
        rv = {
            'success': True
        }
        if use_type is UseType.both.value:
            is_voucher_exhausted = self.is_voucher_exhausted(voucher_id)
            if not is_voucher_exhausted:
                is_voucher_exhausted_for_this_user = self.is_voucher_exhausted_for_this_user(
                    user_id, voucher_id)
                if is_voucher_exhausted_for_this_user:
                    rv['success'] = False
                    rv['msg'] = 'Voucher Invalid for this user'
            else:
                rv['success'] = False
                rv['msg'] = 'This voucher has exhausted'
        elif use_type is UseType.per_user.value:
            is_voucher_exhausted_for_this_user = self.is_voucher_exhausted_for_this_user(
                user_id, voucher_id)
            if is_voucher_exhausted_for_this_user:
                rv['success'] = False
                rv['msg'] = 'Voucher Invalid for this user'
        elif use_type is UseType.global_use.value:
            is_voucher_exhausted = self.is_voucher_exhausted(voucher_id)
            if is_voucher_exhausted:
                rv['success'] = False
                rv['msg'] = 'This voucher has exhausted'
        return rv

    def is_voucher_exhausted(self, voucher_id):
        db = CouponsAlchemyDB()
        total_allowed_uses = self.criteria_obj.usage['no_of_total_uses_allowed']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id})
        if count > total_allowed_uses:
            return True
        return False

    def is_voucher_exhausted_for_this_user(self, user_id, voucher_id):
        db = CouponsAlchemyDB()
        total_per_user_allowed_uses = self.criteria_obj.usage['no_of_uses_allowed_per_user']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id, 'user_id': user_id})
        if count > total_per_user_allowed_uses:
            return True
        return False

    # def update_cache(self):
    #     rule = Rule.find_one(self.id)
    #     rule_key = RULE_CACHE_KEY + rule.id
    #     cache.set(rule_key, rule)


class RuleCriteria(object):
    def __init__(self, **kwargs):
        self.area = kwargs.get('area', list())
        self.area.sort()
        self.brands = kwargs.get('brands', list())
        self.brands.sort()
        self.categories = {
            'in': kwargs.get('categories')['in'],
            'not_in': kwargs.get('categories')['not_in']
        }
        self.categories['in'].sort()
        self.categories['not_in'].sort()
        self.channels = kwargs.get('channels', list())
        self.channels.sort()
        self.city = kwargs.get('city', list())
        self.city.sort()
        self.country = kwargs.get('country', list())
        self.country.sort()
        self.payment_modes = kwargs.get('payment_modes', list())
        self.payment_modes.sort()
        self.products = kwargs.get('products', list())
        self.products.sort()
        self.range_max = kwargs.get('range_max', None)
        self.range_min = kwargs.get('range_min', None)
        self.sellers = kwargs.get('sellers', list())
        self.sellers.sort()
        self.state = kwargs.get('state', list())
        self.state.sort()
        self.storefronts = kwargs.get('storefronts', list())
        self.storefronts.sort()
        self.valid_on_order_no = kwargs.get('valid_on_order_no', list())
        self.valid_on_order_no.sort()
        use_type = kwargs.get('use_type', 0)
        no_of_uses_allowed_per_user = kwargs.get('no_of_uses_allowed_per_user', None)
        no_of_total_uses_allowed = kwargs.get('no_of_total_uses_allowed', None)
        self.usage = {
            'use_type': use_type,
            'no_of_uses_allowed_per_user': no_of_uses_allowed_per_user,
            'no_of_total_uses_allowed': no_of_total_uses_allowed
        }
        self.variants = kwargs.get('variants', list())
        self.variants.sort()
        self.zone = kwargs.get('zone', list())
        self.zone.sort()

    def __eq__(self, other) :
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        return canonicaljson.encode_canonical_json(self.__dict__)


class Benefits(object):
    def __init__(self, **kwargs):
        self.maximum_discount = kwargs.get('max_discount', None)
        self.data = kwargs.get('data', list())
        self.data.sort()

    def __eq__(self, other) :
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        return canonicaljson.encode_canonical_json(self.__dict__)


class BenefitsData(object):
    def __init__(self, **kwargs):
        self.type = kwargs.get('type')
        self.value = kwargs.get('value')
        if self.type == BenefitType.freebie.value:
            self.value.sort()