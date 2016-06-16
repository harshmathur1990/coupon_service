import canonicaljson
import copy
from data import VerificationItemData
from src.enums import UseType, MatchStatus
from src.sqlalchemydb import CouponsAlchemyDB
from utils import fetch_user_details
from src.rules.match_utils import match_list_intersection_atleast_one_common, \
    match_value_in_list, match_user_order_no, match_in_not_in, match_greater_than, \
    match_less_than, match_greater_than_equal_to, match_less_than_equal_to
from src.rules import default_error_message, payment_error_message,\
    order_no_not_valid_error_message, cart_min_error_message, cart_max_error_message,\
    range_min_error_message, range_max_error_message


class RuleCriteria(object):
    # (rule_criteria_attr, order_attr, match_method, callback (optional, if not None, input parameter is Order object))
    criteria_attributes = [
        ('channels', 'channel', match_value_in_list, None),
        ('country', 'country', match_list_intersection_atleast_one_common, None),
        ('state', 'state', match_list_intersection_atleast_one_common, None),
        ('city', 'city', match_list_intersection_atleast_one_common, None),
        ('zone', 'zone', match_list_intersection_atleast_one_common, None),
        ('area', 'area', match_value_in_list, None),
        ('source', 'source', match_value_in_list, None),
        ('payment_modes', 'payment_mode', match_value_in_list, None),
        ('valid_on_order_no', None, match_user_order_no, fetch_user_details)
    ]

    item_attributes = [
        ('brands', 'brand', match_value_in_list, None),
        ('categories', 'category', match_in_not_in, None),
        ('products', 'product', match_in_not_in, None),
        ('sellers', 'seller', match_value_in_list, None),
        ('storefronts', 'storefront', match_list_intersection_atleast_one_common, None),
        ('variants', 'variant', match_value_in_list, None)
    ]

    match_attributes = [
        ('cart_range_min', 'total_price', match_greater_than_equal_to, None),
        ('cart_range_max', 'total_price', match_less_than_equal_to, None),
        ('range_min', 'matching_criteria_total', match_greater_than_equal_to, None),
        ('range_max', 'matching_criteria_total', match_less_than_equal_to, None),
    ]

    message_dict = {
        'cart_range_min': cart_min_error_message,
        'cart_range_max': cart_max_error_message,
        'range_min': range_min_error_message,
        'range_max': range_max_error_message,
        'payment_modes': payment_error_message,
        'valid_on_order_no': order_no_not_valid_error_message
    }

    def __init__(self, **kwargs):
        self.area = kwargs.get('area', None)
        self.brands = kwargs.get('brands', None)

        self.categories = kwargs.get('categories', None)

        if self.categories:
            if 'in' in self.categories and self.categories['in']:
                self.categories['in'].sort()
            if 'not_in' in self.categories and self.categories['not_in']:
                self.categories['not_in'].sort()

        self.channels = kwargs.get('channels', None)

        self.city = kwargs.get('city', None)

        self.country = kwargs.get('country', None)

        self.payment_modes = kwargs.get('payment_modes', None)

        self.source = kwargs.get('source', None)

        self.products = kwargs.get('products', None)
        if self.products:
            if 'in' in self.products and self.products['in']:
                self.products['in'].sort()
            if 'not_in' in self.products and self.products['not_in']:
                self.products['not_in'].sort()

        self.range_max = kwargs.get('range_max', None)
        self.range_min = kwargs.get('range_min', None)
        self.cart_range_max = kwargs.get('cart_range_max', None)
        self.cart_range_min = kwargs.get('cart_range_min', None)
        self.sellers = kwargs.get('sellers', None)

        self.state = kwargs.get('state', None)

        self.storefronts = kwargs.get('storefronts', None)

        self.valid_on_order_no = kwargs.get('valid_on_order_no', None)

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
        self.variants = kwargs.get('variants', None)

        self.zone = kwargs.get('zone', None)
        if self.area:
            self.area.sort()
        if self.brands:
            self.brands.sort()
        if self.channels:
            self.channels.sort()
        if self.city:
            self.city.sort()
        if self.country:
            self.country.sort()
        if self.payment_modes:
            self.payment_modes.sort()
        if self.source:
            self.source.sort()
        if self.sellers:
            self.sellers.sort()
        if self.state:
            self.state.sort()
        if self.storefronts:
            self.storefronts.sort()
        if self.valid_on_order_no:
            self.valid_on_order_no.sort()
        if self.variants:
            self.variants.sort()
        if self.zone:
            self.zone.sort()

    def __eq__(self, other) :
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        self_dict = copy.deepcopy(self.__dict__)
        for key, items in self_dict.items():
            if not items:
                del self_dict[key]
            elif isinstance(items, dict):
                if key is 'usage':
                    if items['use_type'] is UseType.not_available.value:
                        del self_dict[key]
                else:
                    if 'in' in items and not items['in']:
                        del items['in']
                    if 'not_in' in items and not items['not_in']:
                        del items['not_in']
                    if not items:
                        del self_dict[key]

        return canonicaljson.encode_canonical_json(self_dict)

    def match_item(self, item):
        assert isinstance(item, VerificationItemData)
        found_matching = False

        for criteria_attr, item_attr, method, callback in self.item_attributes:
            if method is match_in_not_in:
                # This method must check if the in component is present than criteria must satisfy the in component
                # and if the not in criteria is present, the value must not match not in criteria, it should set
                # found_matching as true if above happens, rest all cases
                # it should return MatchStatus.found_not_matching

                status = method(getattr(self, criteria_attr), getattr(item, item_attr))

                if status is MatchStatus.found_not_matching:
                    return MatchStatus.found_not_matching
                elif status is MatchStatus.found_matching:
                    found_matching = True
            else:
                if getattr(self, criteria_attr) is not None:
                    if method(getattr(self, criteria_attr), getattr(item, item_attr)):
                        found_matching = True
                    else:
                        return MatchStatus.found_not_matching

        if found_matching:
            return MatchStatus.found_matching
        else:
            return MatchStatus.not_found

    def match_criteria(self, order, code):

        found_matching = False

        for criteria_attr, order_attr, method, callback in self.criteria_attributes:
            if getattr(self, criteria_attr) is not None:
                if not callback:
                    if criteria_attr == 'payment_modes' and not order.check_payment_mode:
                        continue
                    if method(getattr(self, criteria_attr), getattr(order, order_attr)):
                        found_matching = True
                    else:
                        error_message = self.message_dict.get(criteria_attr, default_error_message)
                        return MatchStatus.found_not_matching, error_message
                else:
                    if method(getattr(self, criteria_attr), order, callback):
                        found_matching = True
                    else:
                        error_message = self.message_dict.get(criteria_attr, default_error_message)
                        return MatchStatus.found_not_matching, error_message

        if found_matching:
            return MatchStatus.found_matching, None
        else:
            return MatchStatus.not_found, None

    def match(self, order, voucher):
        if order.validate:
            success, error = self.check_usage(order.customer_id, voucher.id_bin, order.order_id)
            if not success:
                return False, None, default_error_message

        status, error = self.match_criteria(order, voucher.code)
        if status is MatchStatus.found_not_matching:
            return False, None, error

        item_id_list = list()
        total = 0.0
        for item in order.items:
            assert isinstance(item, VerificationItemData)
            if not item.blacklisted and self.match_item(item) is not MatchStatus.found_not_matching:
                total += item.price * item.quantity
                item_id_list.append(item.item_id)

        order.matching_criteria_total = total

        if not item_id_list:
            return False, None, default_error_message

        for criteria_attr, order_attr, method, callback in self.match_attributes:
            if getattr(self, criteria_attr) is not None:
                if not method(getattr(self, criteria_attr), getattr(order, order_attr)):
                    error_message = self.message_dict.get(criteria_attr)
                    return False, None, error_message.format(getattr(self, criteria_attr))

        return True, {'total': order.matching_criteria_total, 'item_id_list': item_id_list}, None

    def check_usage(self, user_id, voucher_id, order_id, db=None):
        use_type = self.usage['use_type']
        rv = {
            'success': True,
            'msg': None
        }
        if use_type is UseType.both.value:
            is_voucher_exhausted = self.is_voucher_exhausted(voucher_id, order_id, db)
            if not is_voucher_exhausted:
                is_voucher_exhausted_for_this_user = self.is_voucher_exhausted_for_this_user(
                    user_id, voucher_id, order_id, db)
                if is_voucher_exhausted_for_this_user:
                    rv['success'] = False
                    rv['msg'] = 'This voucher has expired'
            else:
                rv['success'] = False
                rv['msg'] = 'This voucher has expired'
        elif use_type is UseType.per_user.value:
            is_voucher_exhausted_for_this_user = self.is_voucher_exhausted_for_this_user(
                user_id, voucher_id, order_id, db)
            if is_voucher_exhausted_for_this_user:
                rv['success'] = False
                rv['msg'] = 'This voucher has expired'
        elif use_type is UseType.global_use.value:
            is_voucher_exhausted = self.is_voucher_exhausted(voucher_id, order_id, db)
            if is_voucher_exhausted:
                rv['success'] = False
                rv['msg'] = 'This voucher has expired'
        return rv['success'], rv['msg']

    def is_voucher_exhausted(self, voucher_id, order_id, db=None):
        if not db:
            db = CouponsAlchemyDB()
        total_allowed_uses = self.usage['no_of_total_uses_allowed']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id, 'not_args': {'order_id': order_id}})
        if count >= total_allowed_uses:
            return True
        return False

    def is_voucher_exhausted_for_this_user(self, user_id, voucher_id, order_id, db=None):
        if not db:
            db = CouponsAlchemyDB()
        total_per_user_allowed_uses = self.usage['no_of_uses_allowed_per_user']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id, 'user_id': user_id, 'not_args': {'order_id': order_id}})
        if count >= total_per_user_allowed_uses:
            return True
        return False