import datetime
import logging
import json
from vouchers import Vouchers, VoucherTransactionLog
from src.enums import BenefitType, Channels, VoucherTransactionStatus
from rule import Rule
import uuid
from lib.utils import make_api_call
from config import LOCATIONURL, SUBSCRIPTIONURL, USERINFOURL, TOKEN
from data import VerificationItemData
from data import OrderData
logger = logging.getLogger(__name__)


def get_rule(rule_id):
    rule = Rule.find_one(rule_id)
    if rule:
        return rule
    return None


def get_voucher(voucher_code):
    voucher = Vouchers.find_one(voucher_code)
    if voucher and voucher.to_date > datetime.datetime.utcnow():
        return voucher
    return None


def get_benefits(data, coupon_code):
    '''

    :param data: {'rule': Rule, 'items': list of VerificationItemData, 'total': 1000}
    :return:
    '''
    benefit_dict = dict()
    rule = data['rule']
    assert isinstance(rule, Rule), u'rule is not of Type Rule'
    benefits = rule.benefits_obj
    max_discount = benefits.maximum_discount
    benefit_list = benefits.data
    freebie_list = list()
    products_list = list()
    discount = 0.0
    for benefit in benefit_list:
        benefit_type = BenefitType(benefit['type'])
        if benefit_type is BenefitType.freebie:
            freebie_list.append(benefit)
        if benefit_type is BenefitType.amount:
            discount = benefit['value']
            if discount:
                for item in data['items']:
                    product_dict = dict()
                    product_dict['item_id'] = item.variant
                    product_dict['qty'] = item.quantity
                    product_dict['discount'] = (item.quantity * item.price * discount)/data.get('total')
                    products_list.append(product_dict)
        if benefit_type is BenefitType.percentage:
            percentage = benefit['value']
            if percentage:
                discount = percentage * data.get('total') / 100
                if max_discount and discount > max_discount:
                    discount = max_discount
                for item in data['items']:
                    product_dict = dict()
                    product_dict['subscriptionId'] = item.variant
                    product_dict['qty'] = item.quantity
                    product_dict['discount'] = (item.quantity * item.price * discount)/data.get('total')
                    products_list.append(product_dict)
    benefit_dict['products'] = products_list
    benefit_dict['freebies'] = freebie_list
    benefit_dict['totalDiscount'] = discount
    benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
    benefit_dict['channel'] = [Channels(c).name for c in rule.criteria_obj.channels]
    benefit_dict['couponCodes'] = [coupon_code]
    benefit_dict['status'] = 'success'
    return benefit_dict


def apply_benefits(args, benefit):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    voucher_code = args.get('coupon_codes')[0]
    voucher_id = get_voucher(voucher_code).id
    transaction_log = VoucherTransactionLog(**{
        'id': uuid.uuid1().hex,
        'user_id': user_id,
        'voucher_id': voucher_id,
        'order_id': order_id,
        'status': VoucherTransactionStatus.in_progress.value
    })
    return transaction_log.save()


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
    order_data = OrderData(**order_data_dict)
    return True, order_data, None
