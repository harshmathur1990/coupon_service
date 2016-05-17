import canonicaljson

from api.v1.data import VerificationItemData
from src.enums import UseType, MatchStatus, Channels
from src.sqlalchemydb import CouponsAlchemyDB
from lib.exceptions import UserNotFoundException


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
        from lib.utils import get_intersection_of_lists
        found_matching = False

        if self.brands:
            if item.brand in self.brands:
                found_matching = True
            else:
                return MatchStatus.found_not_matching

        if self.categories['in'] or self.categories['not_in']:
           if (self.categories['in'] and get_intersection_of_lists(self.categories['in'], item.category)) \
                   or (self.categories['not_in']
                       and not get_intersection_of_lists(self.categories['not_in'], item.category)):
               found_matching = True
           else:
               return MatchStatus.found_not_matching

        if self.products['in'] or self.products['not_in']:
           if (self.products['in'] and get_intersection_of_lists(self.products['in'], item.product)) \
                   or (self.products['not_in']
                       and not get_intersection_of_lists(self.products['not_in'], item.product)):
               found_matching = True
           else:
               return MatchStatus.found_not_matching

        if self.sellers:
            if item.seller in self.sellers:
                found_matching = True
            else:
                return MatchStatus.found_not_matching

        if self.storefronts:
            if item.storefront in self.storefronts:
                found_matching = True
            else:
                return MatchStatus.found_not_matching

        if self.variants:
            if item.variant in self.variants:
                found_matching = True
            else:
                return MatchStatus.found_not_matching

        if found_matching:
            return MatchStatus.found_matching
        else:
            return MatchStatus.not_found

    def match_criteria(self, order, code):
        from lib.utils import get_intersection_of_lists
        found_matching = False

        if self.valid_on_order_no:
            exact_order_no_list = list()
            min_order_no = None
            for an_order_no in self.valid_on_order_no:
                try:
                    # to convert order nos which are exact integers
                    exact_order_no_list.append(int(an_order_no))
                except ValueError:
                    # to convert order nos which are like 4+ means minimum order no 4
                    if not min_order_no:
                        min_order_no = int(an_order_no[:-1])

            if exact_order_no_list or min_order_no:
                # if minimum order no is given 1 (1+), than the condition is true always.
                # else fetch order details and check if the coupon is valid on
                # that particular order no
                if min_order_no and min_order_no is 1:
                    found_matching = True
                else:
                    from api.v1.utils import fetch_user_details
                    success, order_no, error = fetch_user_details(order.customer_id)
                    if not success:
                        raise UserNotFoundException()
                    order_no += 1
                    order.order_no = order_no
                    if (exact_order_no_list and order.order_no in exact_order_no_list) \
                            or (min_order_no and order.order_no >= min_order_no):
                        found_matching = True
                    else:
                        return MatchStatus.found_not_matching, u'This coupon {} is not applicable on this order'.format(code)

        if self.channels:
            if order.channel in self.channels:
                found_matching = True
            else:
                return MatchStatus.found_not_matching, u'This coupon {} is only valid on orders from {}'.format(
                    code,','.join([Channels(c).name for c in self.channels]))

        if self.country:
            if get_intersection_of_lists(self.country, order.country):
                found_matching = True
            else:
                return MatchStatus.found_not_matching, u'This coupon {} is not valid in your country'.format(code)

        if self.state:
            if get_intersection_of_lists(self.state, order.state):
                found_matching = True
            else:
                return MatchStatus.found_not_matching, u'This coupon {} is not valid in your state'.format(code)

        if self.city:
            if get_intersection_of_lists(self.city, order.city):
                found_matching = True
            else:
                return MatchStatus.found_not_matching, u'This coupon {} is not valid in your city'.format(code)

        if self.zone:
            if get_intersection_of_lists(self.zone, order.zone):
                found_matching = True
            else:
                return MatchStatus.found_not_matching, u'This coupon {} is not valid in your zone'.format(code)

        if self.area:
            if order.area in self.area:
                found_matching = True
            else:
                return MatchStatus.found_not_matching, u'This coupon {} is not valid in your area'.format(code)

        if self.source:
            if order.source in self.source:
                found_matching = True
            else:
                return MatchStatus.found_not_matching, u'This coupon {} is not valid on this order'.format(code)

        if found_matching:
            return MatchStatus.found_matching, None
        else:
            return MatchStatus.not_found, None

    def match(self, order, voucher):
        success, error = self.check_usage(order.customer_id, voucher.id_bin)
        if not success:
            return False, None, u'Coupon {} has expired'.format(voucher.code)

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

        if not item_id_list:
            return False, None, u'No matching items found for this coupon {}'.format(voucher.code)

        if self.cart_range_min and order.total_price < self.cart_range_min:
            return False, None, u'Total Order amount should not be less than {} for coupon code {}'.format(self.cart_range_min, voucher.code)

        if self.cart_range_max and order.total_price > self.cart_range_max:
            return False, None, u'Coupon {} is valid only till max amount {}'.format(voucher.code, self.cart_range_max)

        if self.range_min and total < self.range_min:
            return False, None, u'Total Order amount should not be less than {} for coupon code {}'.format(self.range_min, voucher.code)

        if self.range_max and total > self.range_max:
            return False, None, u'Coupon {} is valid only till max amount {}'.format(voucher.code, self.range_max)

        return True, {'total': total, 'item_id_list': item_id_list}, None

    def check_usage(self, user_id, voucher_id, db=None):
        use_type = self.usage['use_type']
        rv = {
            'success': True,
            'msg': None
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
        return rv['success'], rv['msg']

    def is_voucher_exhausted(self, voucher_id, db=None):
        if not db:
            db = CouponsAlchemyDB()
        total_allowed_uses = self.usage['no_of_total_uses_allowed']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id})
        if count >= total_allowed_uses:
            return True
        return False

    def is_voucher_exhausted_for_this_user(self, user_id, voucher_id, db=None):
        if not db:
            db = CouponsAlchemyDB()
        total_per_user_allowed_uses = self.usage['no_of_uses_allowed_per_user']
        count = db.count("voucher_use_tracker", **{'voucher_id': voucher_id, 'user_id': user_id})
        if count >= total_per_user_allowed_uses:
            return True
        return False