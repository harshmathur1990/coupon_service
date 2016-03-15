from src.enums import *
from rule import Rule, RuleCriteria, Benefits
from vouchers import Vouchers
from utils import get_rule, get_voucher
from data import OrderData, VerificationItemData
import uuid, datetime
import logging
import json
import grequests
from config import LOCATIONURL, SUBSCRIPTIONURL, USERINFOURL

logger = logging.getLogger(__name__)


def validate_for_create_coupon(data):
    error = list()
    success = True

    if data.get('use_type') in [UseType.global_use.value, UseType.both.value]\
            and not data.get('no_of_total_uses_allowed'):
        success = False
        error.append(u'no_of_total_uses_allowed is mandatory if use_type in (global_use, both')

    if data.get('use_type') in [UseType.per_user.value, UseType.both.value]\
            and not data.get('no_of_uses_allowed_per_user'):
        success = False
        error.append(u'no_of_uses_allowed_per_user is mandatory if use_type in (per_user, both')

    if data.get('range_min') and data.get('range_max') and data.get('range_max') <= data.get('range_min'):
        success = False
        error.append(u'range_max must be greater than range_min')

    benefit_count = 0
    if data.get('freebies'):
        benefit_count += 1
    if data.get('amount'):
        benefit_count += 1
    if data.get('percentage'):
        benefit_count += 1

    if benefit_count!= 1:
        success = False
        error.append(u'Benefit must have one of the values in freebies or amount or percentage')

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
                created_by=data.get('user_id'), updated_by=data.get('user_id'))
    return rule


def validate_for_create_voucher(data_dict, rule_id):
    error = list()
    success = True

    if not Rule.find_one(rule_id):
        success = False
        error.append(u'No Rule Exists for rule id {}'.format(data_dict.get('rule_id')))

    if data_dict.get('from') < datetime.datetime.utcnow():
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


def get_item_details(response, total_length, item_to_quantity):
    # returns the list of instances of VerificationItemData
    try:
        items_list = list()
        data_list  = json.loads(response.text)
        if not data_list and len(data_list) != total_length:
            return False, None, 'Invalid Item ids provided'
        for data in data_list:
            item_dict = dict()
            item_dict['brand'] = data.get('brandid')
            item_dict['category'] = [data.get('categoryid')]
            item_dict['product'] = data.get('productid')
            item_dict['seller'] = data.get('sellerid')
            item_dict['storefront'] = data.get('storefront')
            item_dict['variant'] = data.get('variantid')
            item_dict['price'] = data.get('offerprice')
            item_dict['quantity'] = item_to_quantity[data.get('itemid')]
            items_list.append(VerificationItemData(**item_dict))
        return True, items_list, None
    except Exception as e:
        logger.exception(e)
        return False, None, 'Unable to fetch Items'


def get_user_details(response):
    # returns the order no of the user
    try:
        data_list  = json.loads(response.text)
        if not data_list:
            return False, None, u'User Does not exist'
        return True, data_list[0]['ordercount'], None
    except Exception as e:
        logger.exception(e)
        return False, None, 'Unable to fetch Items'


def get_location_details(response):
    # returns a dict containing location information
    try:
        data_list  = json.loads(response.text)
        if not data_list:
            return False, None, u'Area Does not exist'
        data = data_list[0]
        location_dict = dict()
        location_dict['area'] = data.get('areaid')
        location_dict['country'] = [data.get('countryid')]
        location_dict['state'] = [data.get('stateid')]
        location_dict['city'] = [data.get('cityid')]
        location_dict['zone'] = [data.get('zoneid')]
        return True, location_dict, None
    except Exception as e:
        logger.exception(e)
        return False, None, u'Unable to fetch area details'


def fetch_order_detail(args):
    # custom implementation for askmegrocery, this method has to be
    # re-written to integrate with other sites' services
    area_id = args.get('area_id')
    customer_id = args.get('customer_id')
    item_id_list = list()
    item_to_quantity = dict()
    for item in args.get('products', list()):
        item_id_list.append(item.get('item_id'))
        item_to_quantity[item.get('item_id')] = item.get('quantity')
    item_id_list_str = ','.join(item_id_list)

    item_url = SUBSCRIPTIONURL + item_id_list_str + '/'
    location_url = LOCATIONURL + area_id + '/'
    user_info_url = USERINFOURL + customer_id + '/'

    urls = [item_url, location_url, user_info_url]
    rs = (grequests.get(u) for u in urls)
    list_of_responses = grequests.map(rs)
    items = list()
    order_no = 0
    location_dict = dict()
    for index, response in enumerate(list_of_responses):
        if index is 0:
            success, items, error = get_item_details(response, len(item_id_list), item_to_quantity)
            if not success:
                break
        if index is 1:
            success, location_dict, error = get_location_details(response)
            if not success:
                break
        if index is 2:
            success, order_no, error = get_user_details(response)
            if not success:
                break
    if not success:
        return success, None, error
    order_data_dict = dict()
    order_data_dict['order_no'] = order_no
    order_data_dict.update(location_dict)
    order_data_dict['channel'] = args.get('channel')
    order_data_dict['items'] = items
    order_data = OrderData(**order_data_dict)
    return True, order_data, None


def validate_coupon(args):
    # this is where all the magic happens
    coupon_code = args.get('coupon_codes')[0]
    voucher = get_voucher(coupon_code)
    if not voucher:
        False, None, {'error': u'Voucher {} is not valid'.format(coupon_code)}
    rule = get_rule(voucher.rule_id)
    if not rule:
        # should not happen, hence put a logger
        logger.error(u'No rule exists for voucher code {} with rule_id {}'.format(coupon_code, voucher.rule_id))
        return False, None, {'error': u'Voucher {} is not valid'.format(coupon_code)}
    rv = rule.check_usage(args.get('customer_id'), voucher.id)
    if not rv['success']:
        return False, None, rv['msg']
    success, order_details, error = fetch_order_detail(args)
    if not success:
        return success, None, {'error': error}
    success, data = order_details.match(rule)
    if success:
        return success, {'rule': rule, 'items_list': data.get('items'), 'total': data.get('total')}, None
    return success, None, {'error': data}
