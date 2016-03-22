import datetime
import logging
import uuid

from data import OrderData
from rule import Rule, RuleCriteria, Benefits
from src.enums import *
from utils import get_voucher, fetch_order_detail
from vouchers import Vouchers
from lib.utils import get_intersection_of_lists

logger = logging.getLogger(__name__)


def validate_for_create_coupon(data):
    error = list()
    success = True

    rules = data.get('rules')

    for rule in rules:
        criteria = rule.get('criteria')

        if criteria.get('range_max') and criteria.get('range_min') and \
                        criteria.get('range_max') <= criteria.get('range_min'):
            success = False
            error.append(u'range_max must be greater than range_min')

        if criteria.get('cart_range_max') and criteria.get('cart_range_min') and \
                        criteria.get('cart_range_max') <= criteria.get('cart_range_min'):
            success = False
            error.append(u'cart_range_max must be greater than cart_range_min')

        in_categories = criteria.get('categories').get('in')

        not_in_categories = criteria.get('categories').get('not_in')

        if in_categories and not_in_categories and get_intersection_of_lists(in_categories, not_in_categories):
            success = False
            error.append(u'Categories[in] and Categories[not_in] must not have any intersection in a rule')

    return success, error


def create_rule_object(data):
    rule_criteria_kwargs = dict()
    rule_criteria_keys = [
        'brands', 'categories', 'channels', 'valid_on_order_no',
        'payment_modes', 'products', 'range_max',
        'range_min', 'sellers',  'storefronts',
        'use_type', 'no_of_uses_allowed_per_user',
        'no_of_total_uses_allowed', 'variants', 'location'
    ]
    location_keys = [
        'country', 'state', 'city', 'area', 'zone'
    ]
    for a_key in rule_criteria_keys:
        if a_key is not 'location':
            rule_criteria_kwargs[a_key] = data.get(a_key)
        else:
            location = data.get('location')
            for location_key in location_keys:
                rule_criteria_kwargs[location_key] = location.get(location_key)
    rule_criteria = RuleCriteria(**rule_criteria_kwargs)
    freebie_benefit_list = list()
    for freebie in data.get('freebies', list()):
        freebie_dict = dict()
        freebie_dict['type'] = BenefitType.freebie.value
        freebie_dict['value'] = freebie
        freebie_benefit_list.append(freebie_dict)
    amount_benefit = {
        'type': BenefitType.amount.value,
        'value': data.get('amount')
    }
    percentage_benefit = {
        'type': BenefitType.percentage.value,
        'value': data.get('percentage')
    }
    benefit_list = freebie_benefit_list
    benefit_list.append(amount_benefit)
    benefit_list.append(percentage_benefit)
    benefits = Benefits(max_discount=data.get('max_discount'), data=benefit_list)
    id = uuid.uuid1().hex
    rule = Rule(id=id, name=data.get('name'), description=data.get('description'),
                criteria_json=rule_criteria.canonical_json(), benefits_json=benefits.canonical_json(),
                created_by=data.get('user_id'), updated_by=data.get('user_id'), rule_type=data.get('rule_type'))
    return rule


def validate_for_create_voucher(data_dict, rule_id):
    error = list()
    success = True

    if not Rule.find_one(rule_id):
        success = False
        error.append(u'No Rule Exists for rule id {}'.format(data_dict.get('rule_id')))

    if data_dict.get('from').date() < datetime.datetime.utcnow().date():
        success = False
        error.append('Backdated voucher creation is not allowed')

    if data_dict.get('to') < data_dict.get('from'):
        success = False
        error.append(u'Voucher end date must be greater than start date')

    return success, error


def create_voucher_object(data, rule_id, code):
    kwargs = dict()
    id = uuid.uuid1().hex
    kwargs['id'] = id
    kwargs['created_by'] = data.get('user_id')
    kwargs['code'] = code
    kwargs['rule_id'] = rule_id
    kwargs['description'] = data.get('description')
    kwargs['from'] = data.get('from')
    kwargs['to'] = data.get('to')
    kwargs['updated_by'] = data.get('user_id')
    voucher = Vouchers(**kwargs)
    return voucher


def validate_coupon(args):
    success, order, error = fetch_order_detail(args)
    assert isinstance(order, OrderData)
    if not success:
        return success, None, error

    for a_coupon in args.get('coupon_codes'):
        voucher = get_voucher(a_coupon)
        if not voucher:
            failed_dict = {
                'voucher': a_coupon,
                'error': u'Voucher does not exist'
            }
            order.failed_vouchers.append(failed_dict)
            continue
        voucher.match(order)
        if not order.can_accomodate_new_vouchers:
            break

    if order.existing_vouchers:
        return True, order, None
    else:
        return False, None, u'No matching items found for these coupons'
