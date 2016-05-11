import binascii
import hashlib
import logging

import canonicaljson
from data import OrderData, VerificationItemData
from lib.utils import get_intersection_of_lists
from src.enums import UseType, BenefitType, Channels
from src.sqlalchemydb import CouponsAlchemyDB

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
        self.criteria_obj = kwargs.get('criteria_obj')
        self.criteria_json = kwargs.get('criteria_json')
        self.blacklist_criteria_obj = kwargs.get('blacklist_criteria_obj')
        self.blacklist_criteria_json = kwargs.get('blacklist_criteria_json')
        self.benefits_json = kwargs.get('benefits_json')
        self.benefits_obj = kwargs.get('benefits_obj')
        self.sha2hash = kwargs.get('sha2hash')
        self.active = kwargs.get('active', True)
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        if not self.criteria_obj:
            criteria_dict = canonicaljson.json.loads(self.criteria_json)
            self.criteria_obj = RuleCriteria(**criteria_dict)
        if not self.blacklist_criteria_obj and self.blacklist_criteria_json is not None:
            blacklist_criteria_dict = canonicaljson.json.loads(self.blacklist_criteria_json)
            self.blacklist_criteria_obj = RuleCriteria(**blacklist_criteria_dict)
        if not self.benefits_obj:
            benefits_dict = canonicaljson.json.loads(self.benefits_json)
            self.benefits_obj = Benefits(**benefits_dict)

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin()
        # update_cache = False
        try:
            # check if the rule being created already exists, if yes, just return rule id
            existing_rule = db.find_one("rule", **{'id': self.id_bin})
            if existing_rule:
                # call is to update the existing rule with new attributes, just update and save it
                # update_cache = True
                logger.error('Trying to update an existing rule {}'.format(self.__dict__))
                assert False, "A Rule is immutable."
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
            db.commit()
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False
        # else:
        #     db.commit()
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
        values['criteria_json'] = self.criteria_json
        values['blacklist_criteria_json'] = self.blacklist_criteria_json
        values['benefits_json'] = self.benefits_json
        un_hashed_string = unicode(self.criteria_json) + \
            unicode(self.blacklist_criteria_json) + unicode(self.benefits_json)
        values['sha2hash'] = hashlib.sha256(un_hashed_string).hexdigest()
        values['active'] = self.active
        if self.created_by:
            values['created_by'] = self.created_by
        if self.updated_by:
            values['updated_by'] = self.updated_by
        return values

    def __eq__(self, other):
        if self.criteria_obj == other.criteria_obj and \
                self.benefits_obj == other.benefits_obj:
            return True
        return False

    @staticmethod
    def find_one(id, db=None):
        id = binascii.a2b_hex(id)
        if not db:
            db = CouponsAlchemyDB()
        rule_dict = db.find_one("rule", **{'id': id})
        if rule_dict:
            rule_dict['id'] = binascii.b2a_hex(rule_dict['id'])
            rule = Rule(**rule_dict)
            return rule
        return False

    def check_usage(self, user_id, voucher_id, db=None):
        use_type = self.criteria_obj.usage['use_type']
        rv = {
            'success': True
        }
        if use_type is UseType.both.value:
            is_voucher_exhausted = self.is_voucher_exhausted(voucher_id, db)
            if not is_voucher_exhausted:
                is_voucher_exhausted_for_this_user = self.is_voucher_exhausted_for_this_user(
                    user_id, voucher_id, db)
                if is_voucher_exhausted_for_this_user:
                    rv['success'] = False
                    rv['msg'] = 'This voucher has expired'
            else:
                rv['success'] = False
                rv['msg'] = 'This voucher has expired'
        elif use_type is UseType.per_user.value:
            is_voucher_exhausted_for_this_user = self.is_voucher_exhausted_for_this_user(
                user_id, voucher_id, db)
            if is_voucher_exhausted_for_this_user:
                rv['success'] = False
                rv['msg'] = 'This voucher has expired'
        elif use_type is UseType.global_use.value:
            is_voucher_exhausted = self.is_voucher_exhausted(voucher_id, db)
            if is_voucher_exhausted:
                rv['success'] = False
                rv['msg'] = 'This voucher has expired'
        return rv

    def is_voucher_exhausted(self, voucher_id, db=None):
        if not db:
            db = CouponsAlchemyDB()
        total_allowed_uses = self.criteria_obj.usage['no_of_total_uses_allowed']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id})
        if count >= total_allowed_uses:
            return True
        return False

    def is_voucher_exhausted_for_this_user(self, user_id, voucher_id, db=None):
        if not db:
            db = CouponsAlchemyDB()
        total_per_user_allowed_uses = self.criteria_obj.usage['no_of_uses_allowed_per_user']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id, 'user_id': user_id})
        if count >= total_per_user_allowed_uses:
            return True
        return False

    def match_rule_blacklist_criteria(self, order):

        criteria_obj = self.blacklist_criteria_obj

        success = None

        if criteria_obj.valid_on_order_no:
            exact_order_no_list = list()
            min_order_no = None
            for an_order_no in criteria_obj.valid_on_order_no:
                try:
                    # to convert order nos which are exact integers
                    exact_order_no_list.append(int(an_order_no))
                except ValueError:
                    # to convert order nos which are like 4+ means minimum order no 4
                    if not min_order_no:
                        min_order_no = int(an_order_no[:-1])
            if (exact_order_no_list and order.order_no not in exact_order_no_list) or \
                    (min_order_no and order.order_no < min_order_no):
                return False
            if exact_order_no_list and order.order_no in exact_order_no_list:
                success = True
            if min_order_no and order.order_no >= min_order_no:
                success = True

        if criteria_obj.channels:
            if order.channel not in criteria_obj.channels:
                return False
            else:
                success = True

        if criteria_obj.country:
            if not get_intersection_of_lists(criteria_obj.country, order.country):
                return False
            else:
                success = True

        if criteria_obj.state:
            if not get_intersection_of_lists(criteria_obj.state, order.state):
                return False
            else:
                success = True

        if criteria_obj.city:
            if not get_intersection_of_lists(criteria_obj.city, order.city):
                return False
            else:
                success = True

        if criteria_obj.zone:
            if not get_intersection_of_lists(self.criteria_obj.zone, order.zone):
                return False
            else:
                success = True

        if criteria_obj.area:
            if order.area not in criteria_obj.area:
                return False
            else:
                success = True

        if criteria_obj.source:
            if order.source not in criteria_obj.source:
                return False
            else:
                success = True

        return success

    def match_rule_criteria(self, order, code):
        criteria_obj = self.criteria_obj
        if criteria_obj.valid_on_order_no:
            exact_order_no_list = list()
            min_order_no = None
            for an_order_no in criteria_obj.valid_on_order_no:
                try:
                    # to convert order nos which are exact integers
                    exact_order_no_list.append(int(an_order_no))
                except ValueError:
                    # to convert order nos which are like 4+ means minimum order no 4
                    if not min_order_no:
                        min_order_no = int(an_order_no[:-1])
            if (exact_order_no_list and order.order_no not in exact_order_no_list) or \
                    (min_order_no and order.order_no < min_order_no):
                return False, u'This coupon {} is not applicable on this order'.format(code)
        if criteria_obj.channels and order.channel not in criteria_obj.channels:
            return False, u'This coupon {} is only valid on orders from {}'.format(code,
                ','.join([Channels(c).name for c in criteria_obj.channels]))
        if criteria_obj.country and not get_intersection_of_lists(criteria_obj.country, order.country):
            return False, u'This coupon {} is not valid in your country'.format(code)
        if criteria_obj.state and not get_intersection_of_lists(criteria_obj.state, order.state):
            return False, u'This coupon {} is not valid in your state'.format(code)
        if criteria_obj.city and not get_intersection_of_lists(criteria_obj.city, order.city):
            return False, u'This coupon {} is not valid in your city'.format(code)
        if criteria_obj.zone and not get_intersection_of_lists(self.criteria_obj.zone, order.zone):
            return False, u'This coupon {} is not valid in your zone'.format(code)
        if criteria_obj.area and order.area not in criteria_obj.area:
            return False, u'This coupon {} is not valid in your area'.format(code)
        if criteria_obj.source and order.source not in criteria_obj.source:
            return False, u'This coupon {} is not valid on this order'.format(code)
        return True, None

    def blacklist_items(self, order, code):
        if not self.blacklist_criteria_obj:
            return
        success = self.match_rule_blacklist_criteria(order)
        if success is False:
            return
        for item in order.items:
            if not item.blacklisted and self.blacklist_criteria_obj.match_item_to_blacklist(item):
                item.blacklisted = True
                order.total_price -= item.price * item.quantity

    def match(self, order, code):
        assert isinstance(order, OrderData)

        self.blacklist_items(order, code)

        success, error = self.match_rule_criteria(order, code)
        if not success:
            return False, None, error

        subscription_id_list = list()
        total = 0.0
        for item in order.items:
            assert isinstance(item, VerificationItemData)
            if not item.blacklisted and self.criteria_obj.match_item(item):
                total += item.price * item.quantity
                subscription_id_list.append(item.subscription_id)

        if not subscription_id_list:
            return False, None, u'No matching items found for this coupon {}'.format(code)

        if self.criteria_obj.cart_range_min and order.total_price < self.criteria_obj.cart_range_min:
            return False, u'Total Order amount should not be less than {} for coupon code {}'.format(self.criteria_obj.cart_range_min, code)
        if self.criteria_obj.cart_range_max and order.total_price > self.criteria_obj.cart_range_max:
            return False, u'Coupon {} is valid only till max amount {}'.format(code, self.criteria_obj.cart_range_max)
        if self.criteria_obj.range_min and total < self.criteria_obj.range_min:
            return False, None, u'Total Order amount should not be less than {} for coupon code {}'.format(self.criteria_obj.range_min, code)
        if self.criteria_obj.range_max and total > self.criteria_obj.range_max:
            return False, None, u'Coupon {} is valid only till max amount {}'.format(code, self.criteria_obj.range_max)

        return True, {'total': total, 'subscription_id_list': subscription_id_list}, None


class RuleCriteria(object):
    def __init__(self, **kwargs):
        self.area = kwargs.get('area', list())
        self.brands = kwargs.get('brands', list())
        self.brands.sort()
        default_in_not_in = dict()
        default_in_not_in['in'] = list()
        default_in_not_in['not_in'] = list()
        category = kwargs.get('categories', default_in_not_in)
        self.categories = {
            'in': category.get('in', list()),
            'not_in': category.get('not_in', list())
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
        self.source = kwargs.get('source', list())
        self.source.sort()
        product = kwargs.get('products', default_in_not_in)
        self.products = {
            'in': product.get('in', list()),
            'not_in': product.get('not_in', list())
        }
        self.products['in'].sort()
        self.products['not_in'].sort()
        self.range_max = kwargs.get('range_max', None)
        self.range_min = kwargs.get('range_min', None)
        self.cart_range_max = kwargs.get('cart_range_max', None)
        self.cart_range_min = kwargs.get('cart_range_min', None)
        self.sellers = kwargs.get('sellers', list())
        self.sellers.sort()
        self.state = kwargs.get('state', list())
        self.state.sort()
        self.storefronts = kwargs.get('storefronts', list())
        self.storefronts.sort()
        self.valid_on_order_no = kwargs.get('valid_on_order_no', list())
        self.valid_on_order_no.sort()
        if kwargs.get('usage'):
            self.usage = kwargs.get('usage')
        else:
            no_of_uses_allowed_per_user = kwargs.get('no_of_uses_allowed_per_user', None)
            no_of_total_uses_allowed = kwargs.get('no_of_total_uses_allowed', None)
            self.usage = {
                'no_of_uses_allowed_per_user': no_of_uses_allowed_per_user,
                'no_of_total_uses_allowed': no_of_total_uses_allowed
            }
            if self.usage.get('no_of_uses_allowed_per_user') and self.usage.get('no_of_total_uses_allowed'):
                self.usage['use_type'] = UseType.both.value
            elif self.usage.get('no_of_uses_allowed_per_user'):
                self.usage['use_type'] = UseType.per_user.value
            elif self.usage.get('no_of_total_uses_allowed'):
                self.usage['use_type'] = UseType.global_use.value
            else:
                self.usage['use_type'] = UseType.not_available.value
        self.variants = kwargs.get('variants', list())
        self.variants.sort()
        self.zone = kwargs.get('zone', list())
        self.zone.sort()

    def __eq__(self, other) :
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        return canonicaljson.encode_canonical_json(self.__dict__)

    def match_item(self, item):
        assert isinstance(item, VerificationItemData)
        if self.brands and item.brand not in self.brands:
            return False
        if (self.categories['in'] and not get_intersection_of_lists(self.categories['in'], item.category)) or \
                (self.categories['not_in'] and get_intersection_of_lists(self.categories['not_in'], item.category)):
            return False

        if (self.products['in'] and not get_intersection_of_lists(self.products['in'], item.product)) or \
                (self.products['not_in'] and get_intersection_of_lists(self.products['not_in'], item.product)):
            return False

        if self.sellers and item.seller not in self.sellers:
            return False
        if self.storefronts and item.storefront not in self.storefronts:
            return False
        if self.variants and item.variant not in self.variants:
            return False

        return True

    def match_item_to_blacklist(self, item):
        assert isinstance(item, VerificationItemData)
        success = None

        if self.brands:
            if item.brand not in self.brands:
                return False
            else:
                success = True

        if (self.categories['in'] and not get_intersection_of_lists(self.categories['in'], item.category)) or \
                (self.categories['not_in'] and get_intersection_of_lists(self.categories['not_in'], item.category)):
            return False

        if self.categories['in'] and get_intersection_of_lists(self.categories['in'], item.category):
            success = True

        if self.categories['not_in'] and not get_intersection_of_lists(self.categories['not_in'], item.category):
            success = True

        if (self.products['in'] and not get_intersection_of_lists(self.products['in'], item.product)) or \
                (self.products['not_in'] and get_intersection_of_lists(self.products['not_in'], item.product)):
            return False

        if self.products['in'] and get_intersection_of_lists(self.products['in'], item.product):
            success = True

        if self.products['not_in'] and not get_intersection_of_lists(self.products['not_in'], item.product):
            success = True

        if self.sellers:
            if item.seller not in self.sellers:
                return False
            else:
                success = True

        if self.storefronts:
            if item.storefront not in self.storefronts:
                return False
            else:
                success = True
        if self.variants:
            if item.variant not in self.variants:
                return False
            else:
                success = True

        return success


class Benefits(object):
    def __init__(self, **kwargs):
        self.max_discount = kwargs.get('max_discount', kwargs.get('maximum_discount', None))
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