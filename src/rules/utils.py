import datetime
import json
import logging
import uuid

from config import LOCATIONURL, SUBSCRIPTIONURL, USERINFOURL, TOKEN
from data import OrderData
from data import VerificationItemData
from lib.utils import make_api_call
from src.sqlalchemydb import CouponsAlchemyDB
from vouchers import Vouchers, VoucherTransactionLog
from rule import Rule, RuleCriteria, Benefits
from src.enums import *

logger = logging.getLogger(__name__)


def get_rule(rule_id):
    rule = Rule.find_one(rule_id)
    if rule:
        return rule
    return None


def get_voucher(voucher_code):
    voucher = Vouchers.find_one(voucher_code)
    now = datetime.datetime.utcnow()
    if voucher and voucher.from_date <= now <= voucher.to_date:
        return voucher
    return None


def get_benefits(order):
    assert isinstance(order, OrderData)
    freebie_list = list()
    products_list = list()
    benefit_dict = dict()
    for existing_voucher in order.existing_vouchers:
        rule = existing_voucher['voucher'].rule
        benefits = rule.benefits_obj
        benefit_list = benefits.data
        discount = 0.0
        total = existing_voucher['total']
        subscription_id_list = existing_voucher['subscription_id_list']
        max_discount = benefits.maximum_discount
        for benefit in benefit_list:
            benefit_type = BenefitType(benefit['type'])
            if benefit_type is BenefitType.freebie:
                freebie_list.append(benefit['value'])
            if benefit_type is BenefitType.amount and benefit['value']:
                if max_discount and benefit['value'] > max_discount:
                    discount = max_discount
                else:
                    discount = benefit['value']
                for item in order.items:
                    product_dict = dict()
                    product_dict['subscriptionId'] = item.subscription_id
                    product_dict['quantity'] = item.quantity
                    product_dict['discount'] = 0.0
                    products_list.append(product_dict)
                    if item.subscription_id in subscription_id_list:
                        product_dict['discount'] = (item.quantity * item.price * discount)/total
            if benefit_type is BenefitType.percentage and benefit['value']:
                percentage = benefit['value']
                discount = percentage * total / 100
                if max_discount and discount > max_discount:
                    discount = max_discount
                for item in order.items:
                    product_dict = dict()
                    product_dict['subscriptionId'] = item.subscription_id
                    product_dict['quantity'] = item.quantity
                    product_dict['discount'] = 0.0
                    products_list.append(product_dict)
                    if item.subscription_id in subscription_id_list:
                        product_dict['discount'] = (item.quantity * item.price * discount)/total
    benefit_dict['products'] = products_list
    benefit_dict['freebies'] = freebie_list
    benefit_dict['totalDiscount'] = discount
    benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
    benefit_dict['channel'] = [Channels(c).name for c in rule.criteria_obj.channels]
    benefit_dict['couponCodes'] = [existing_voucher['voucher'].code for existing_voucher in order.existing_vouchers]
    benefit_dict['status'] = 'success'
    return benefit_dict


def apply_benefits(args, order):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    db = CouponsAlchemyDB()
    db.begin()
    try:
        for existing_voucher in order.existing_vouchers:
            voucher_id = existing_voucher['voucher'].id
            transaction_log = VoucherTransactionLog(**{
                'id': uuid.uuid1().hex,
                'user_id': user_id,
                'voucher_id': voucher_id,
                'order_id': order_id,
                'status': VoucherTransactionStatus.in_progress.value
            })
            transaction_log.save(db)
    except Exception as e:
        logger.exception(e)
        db.rollback()
        return False
    else:
        db.commit()
    return True


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
            item_dict['subscription_id'] = data.get('itemid')
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

    item_id_list_str = ','.join(str(v) for v in item_id_list)

    item_url = SUBSCRIPTIONURL + item_id_list_str + '/'
    location_url = LOCATIONURL + str(area_id) + '/'
    user_info_url = USERINFOURL + str(customer_id) + '/'

    urls = [item_url, location_url, user_info_url]

    headers = {
        'Authorization': TOKEN
    }

    list_of_responses = make_api_call(urls, headers=headers)

    items = list()
    order_no = 0
    location_dict = dict()

    for index, response in enumerate(list_of_responses):
        if index is 0:
            success, items, error = get_item_details(
                response, len(item_id_list), item_to_quantity)
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
    order_data_dict['customer_id'] = args.get('customer_id')
    order_data = OrderData(**order_data_dict)
    return True, order_data, None


def save_rule_list(rule_list):
    rule_id_list = list()
    for rule in rule_list:
        rule.save()
        rule_id_list.append(rule.id)
    return rule_id_list


def create_voucher_object(data, rule_id_list, code):
    kwargs = dict()
    id = uuid.uuid1().hex
    kwargs['id'] = id
    kwargs['created_by'] = data.get('user_id')
    kwargs['code'] = code
    kwargs['rules'] = ','.join(rule_id_list)
    kwargs['description'] = data.get('description')
    kwargs['from'] = data.get('from')
    kwargs['to'] = data.get('to')
    kwargs['updated_by'] = data.get('user_id')
    kwargs['custom'] = data.get('custom')
    voucher = Vouchers(**kwargs)
    return voucher


def save_vouchers(args, rule_id_list):
    success_list = list()
    error_list = list()
    code_list = set(args.get('code'))
    for code in code_list:
        voucher = create_voucher_object(args, rule_id_list, code)
        success = voucher.save()
        if not success:
            error = {
                'code': code,
                'reason': u'{} already exists'.format(code)
            }
            error_list.append(error)
        else:
            success_list.append(success)
    return success_list, error_list


def create_rule_object(data, type, user_id=None):
    criteria = data.get('criteria')
    benefits = data.get('benefits')
    description = data.get('description')
    rule_criteria_kwargs = dict()
    rule_criteria_keys = [
        'brands', 'categories', 'channels', 'valid_on_order_no',
        'payment_modes', 'products', 'range_max', 'cart_range_min',
        'range_min', 'sellers', 'storefronts', 'cart_range_max',
        'no_of_uses_allowed_per_user', 'no_of_total_uses_allowed',
        'variants', 'location.country', 'location.state',
        'location.city', 'location.area', 'location.zone'
    ]

    for a_key in rule_criteria_keys:
        keys = a_key.split('.')
        if len(keys) == 2:
            rule_criteria_kwargs[keys[1]] = criteria.get(keys[0], dict()).get(keys[1])
        else:
            rule_criteria_kwargs[keys[0]] = criteria.get(keys[0])
    rule_criteria = RuleCriteria(**rule_criteria_kwargs)
    freebie_benefit_list = list()
    for freebie in benefits.get('freebies', list()):
        freebie_dict = dict()
        freebie_dict['type'] = BenefitType.freebie.value
        freebie_dict['value'] = freebie
        freebie_benefit_list.append(freebie_dict)
    amount_benefit = {
        'type': BenefitType.amount.value,
        'value': benefits.get('amount')
    }
    percentage_benefit = {
        'type': BenefitType.percentage.value,
        'value': benefits.get('percentage')
    }
    benefit_list = freebie_benefit_list
    benefit_list.append(amount_benefit)
    benefit_list.append(percentage_benefit)
    benefits = Benefits(max_discount=benefits.get('max_discount'), data=benefit_list)
    id = uuid.uuid1().hex
    rule = Rule(id=id, description=description,
                criteria_json=rule_criteria.canonical_json(), benefits_json=benefits.canonical_json(),
                created_by=user_id, updated_by=user_id, type=type)
    return rule


def create_rule_list(args):
    rule_list = list()
    for rule in args.get('rules', list()):
        rule_list.append(create_rule_object(rule, args.get('type'), args.get('user_id')))
    return rule_list


def create_and_save_rule_list(args):
    rule_list = create_rule_list(args)
    return save_rule_list(rule_list), rule_list