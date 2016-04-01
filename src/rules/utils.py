import datetime
import json
import logging
import uuid
import binascii
from config import LOCATIONURL, SUBSCRIPTIONURL, USERINFOURL, TOKEN
from data import OrderData
from data import VerificationItemData
from lib.utils import make_api_call, get_intersection_of_lists
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
        return voucher, None
    elif voucher and now > voucher.to_date:
        db = CouponsAlchemyDB()
        db.delete_row("vouchers", **{'code': voucher.code})
        if voucher.type is not VoucherType.regular_coupon:
            db.delete_row("auto_freebie_search", **{'voucher_id': voucher.id_bin})
        return None, u'The voucher {} has expired'.format(voucher.code)
    else:
        return None, u'The voucher {} does not exist'.format(voucher_code)


def get_benefits(order):
    assert isinstance(order, OrderData)
    products_dict = dict()
    benefits_list = list()
    payment_modes_list = list()
    channels_list = list()
    for item in order.items:
        product_dict = dict()
        product_dict['itemid'] = item.subscription_id
        product_dict['quantity'] = item.quantity
        product_dict['discount'] = 0.0
        products_dict[item.subscription_id] = product_dict
    for existing_voucher in order.existing_vouchers:
        rules = existing_voucher['voucher'].rules_list
        for rule in rules:
            benefits = rule.benefits_obj
            benefit_list = benefits.data
            total = existing_voucher['total']
            subscription_id_list = existing_voucher['subscription_id_list']
            max_discount = benefits.max_discount
            benefit_dict = dict()
            for benefit in benefit_list:
                if not benefit['value']:
                    continue
                discount = 0.0
                freebie_list = list()
                benefit_type = BenefitType(benefit['type'])
                if benefit_type is BenefitType.freebie:
                    freebie_list.append(benefit['value'])
                else:
                    if benefit_type is BenefitType.amount and benefit['value']:
                        discount = benefit['value']
                    elif benefit_type is BenefitType.percentage and benefit['value']:
                        percentage = benefit['value']
                        discount = percentage * total / 100
                    if max_discount and discount > max_discount:
                        discount = max_discount
                    for subscriptionId in subscription_id_list:
                        item_discount = (item.quantity * item.price * discount)/total
                        products_dict[subscriptionId]['discount'] = max(
                            products_dict[subscriptionId]['discount'], item_discount)
                benefit_dict['couponCode'] = existing_voucher['voucher'].code
                benefit_dict['discount'] = discount
                benefit_dict['freebies'] = freebie_list
                benefit_dict['items'] = subscription_id_list
                benefit_dict['type'] = existing_voucher['voucher'].type
                benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
                benefit_dict['channel'] = [Channels(c).value for c in rule.criteria_obj.channels]
                benefits_list.append(benefit_dict)
                if not payment_modes_list:
                    payment_modes_list = benefit_dict['paymentMode']
                else:
                    payment_modes_list = get_intersection_of_lists(payment_modes_list, benefit_dict['paymentMode'])
                if not channels_list:
                    channels_list = benefit_dict['channel']
                else:
                    channels_list = get_intersection_of_lists(channels_list, benefit_dict['channel'])
    total_discount = 0.0
    products_list = list()
    for item in products_dict:
        product_dict = products_dict[item]
        products_list.append(product_dict)
        total_discount += product_dict['discount']

    response_dict = dict()

    response_dict['products'] = products_list
    response_dict['benefits'] = benefits_list
    response_dict['totalDiscount'] = total_discount
    response_dict['paymentMode'] = payment_modes_list
    response_dict['channel'] = channels_list
    response_dict['couponCodes'] = [existing_voucher['voucher'].code for existing_voucher in order.existing_vouchers]
    return response_dict


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
    success = True
    error = ''

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

    order_no += 1
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
    kwargs['type'] = data.get('type')
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
                'error': u'{} already exists'.format(code),
                'reason': u'{} already exists'.format(code)
            }
            error_list.append(error)
        else:
            success_list.append(success)
    return success_list, error_list


def create_rule_object(data, user_id=None):
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
        if keys[0] not in criteria:
            continue
        if len(keys) == 2:
            if keys[1] not in criteria[keys[0]]:
                continue
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
                created_by=user_id, updated_by=user_id, criteria_obj=rule_criteria, benefits_obj=benefits)
    return rule


def create_rule_list(args):
    rule_list = list()
    for rule in args.get('rules', list()):
        rule_list.append(create_rule_object(rule, args.get('user_id')))
    return rule_list


def create_and_save_rule_list(args):
    rule_list = create_rule_list(args)
    return save_rule_list(rule_list), rule_list


def get_where_clauses(variant_total_map):
    variable_dict = dict()
    final_query = ""
    template = '(`variants`= :? and (`range_min` is null or `range_min` <= :?) and (`range_max` is null or `range_max` >= :?))'
    for variant, total in variant_total_map.items():
        variant_key = 'variant_'+str(variant)
        total_key = 'total_'+str(variant)
        variable_dict[variant_key] = variant
        variable_dict[total_key] = total
        query = template.replace('?', variant_key, 1)
        query = query.replace('?', total_key)
        if not final_query:
            final_query += query
        else:
            final_query += 'or ' + query
    return final_query, variable_dict


def fetch_auto_benefits(order, freebie_type=VoucherType.regular_freebie):
    assert isinstance(order, OrderData)
    variant_total_map = dict()
    item_list = list()
    subscription_variant_map = dict()
    if freebie_type is VoucherType.auto_freebie:
        for item in order.items:
            variant_total_map[item.variant] = variant_total_map.get(item.variant, 0.0) + (item.price * item.quantity)
            list_of_subscription_id = subscription_variant_map.get(item.variant, list())
            list_of_subscription_id.append(item.subscription_id)
            subscription_variant_map[item.variant] = list_of_subscription_id
        where_clause, params = get_where_clauses(variant_total_map)
        sql = 'select  v.*,a.`type`, a.`variants`, a.`zone`  from `vouchers` v join (select * from `auto_freebie_search` where (type = :type and zone in :zone and ('+where_clause+') and (cart_range_min is null or cart_range_min <= :ordertotal) and (cart_range_max is null or cart_range_max >= :ordertotal) and :now > `from` and :now < `to`)) a'
    else:
        for item in order.items:
            item_list.append(item.subscription_id)
        params = dict()
        sql = 'select v.*,a.`type`, a.`variants`, a.`zone` from `vouchers` v join (select * from `auto_freebie_search` where (type = :type and zone in :zone and (cart_range_min is null or cart_range_min <= :ordertotal) and (cart_range_max is null or cart_range_max >= :ordertotal) and :now > `from` and :now < `to`)) a'
    params['ordertotal'] = order.total_price
    params['type'] = freebie_type.value
    params['zone'] = order.zone
    params['now'] = datetime.datetime.utcnow()
    db = CouponsAlchemyDB()
    l = db.execute_raw_sql(sql, params)
    if not l:
        return
    for voucher_dict in l:
        voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
        effectiveVoucher = Vouchers(**voucher_dict)
        effectiveVoucher.get_rule()
        success_dict = {
                'voucher': effectiveVoucher,
            }
        if freebie_type is VoucherType.auto_freebie:
            success_dict['total'] = variant_total_map[voucher_dict['variants']]
            success_dict['subscription_id_list'] = subscription_variant_map[voucher_dict['variants']]
        else:
            success_dict['total'] = order.total_price
            success_dict['subscription_id_list'] = item_list
        order.existing_vouchers.append(success_dict)
