from rule import Rule
from src.enums import Channels
from lib.utils import get_intersection_of_lists


class VerificationItemData(object):
    def __init__(self, **kwargs):
        self.brand = kwargs.get('brand')
        self.category = kwargs.get('category') # will be a list
        self.product = kwargs.get('product')
        self.seller = kwargs.get('seller')
        self.storefront = kwargs.get('storefront')
        self.variant = kwargs.get('variant')
        self.price = kwargs.get('price')
        self.quantity = kwargs.get('quantity')
        self.discounted = False
        self.subscription_id = kwargs.get('subscription_id')

    def match(self, rule):
        assert isinstance(rule, Rule), "rule is not an instance of Rule"
        rule_criteria = rule.criteria_obj
        if rule_criteria.brands and self.brand not in rule_criteria.brands:
            return False
        if not self.in_category(rule_criteria.categories['in']) or \
                not self.not_in_category(rule_criteria.categories['not_in']):
            return False
        if rule_criteria.products and self.product not in rule_criteria.products:
            return False
        if rule_criteria.sellers and self.seller not in rule_criteria.sellers:
            return False
        if rule_criteria.storefronts and self.storefront not in rule_criteria.storefronts:
            return False
        if rule_criteria.variants and self.variant not in rule_criteria.variants:
            return False
        self.discounted = True
        return True

    def in_category(self, categories):
        if get_intersection_of_lists(self.category, categories):
            return True
        return False

    def not_in_category(self, categories):
        return not self.in_category(categories)


class OrderData(object):
    def __init__(self, **kwargs):
        self.order_no = kwargs.get('order_no')
        self.country = kwargs.get('country')  #list
        self.state = kwargs.get('state')  # can and will be treated as list ex: Haryana/Delhi
        self.city = kwargs.get('city')  # treated as list for same reason above
        self.area = kwargs.get('area')
        self.zone = kwargs.get('zone')  # list
        self.channel = kwargs.get('channel')
        self.items = kwargs.get('items')  # list of instances of VerificationItemData
        self.total_price = 0.0
        for item in self.items:
            self.total_price += item.price * item.quantity

    def match(self, rule):
        assert isinstance(rule, Rule), "rule is not an instance of Rule"
        if rule.criteria_obj.range_min and self.total_price < rule.criteria_obj.range_min:
            return False, u'Total Order price is less than minimum {}'.format(rule.criteria_obj.range_min)
        if rule.criteria_obj.range_max and self.total_price > rule.criteria_obj.range_max:
            return False, u'Coupon is valid only till max amount {}'.format(rule.criteria_obj.range_max)
        if rule.criteria_obj.valid_on_order_no and self.order_no not in rule.criteria_obj.valid_on_order_no:
            return False, u'This coupon is only valid on orders {}'.format(
                ','.join(rule.criteria_obj.valid_on_order_no))
        if rule.criteria_obj.channels and self.channel in rule.criteria_obj.channels:
            return False, u'This coupon is only valid on orders from {}'.format(
                ','.join([Channels(c).name for c in rule.criteria_obj.channels]))
        if rule.criteria_obj.country and not get_intersection_of_lists(rule.criteria_obj.country, self.country):
            return False, u'This coupon is not valid in your country'
        if rule.criteria_obj.state and not get_intersection_of_lists(rule.criteria_obj.state, self.state):
            return False, u'This coupon is not valid in your state'
        if rule.criteria_obj.city and not get_intersection_of_lists(rule.criteria_obj.city, self.city):
            return False, u'This coupon is not valid in your city'
        if rule.criteria_obj.zone and not get_intersection_of_lists(rule.criteria_obj.zone, self.zone):
            return False, u'This coupon is not valid in your area'
        if rule.criteria_obj.area and self.area not in rule.criteria_obj.area:
            return False, u'This coupon is not valid in your area'
        matching_items = list()
        total = 0.0
        for item in self.items:
            if item.match(rule):
                total += item.price * item.quantity
            matching_items.append(item)
        if not matching_items:
            return False, None, u'No matching items found for this coupon'

        return True, {'items': matching_items, 'total': total}

