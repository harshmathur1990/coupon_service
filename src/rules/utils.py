import datetime
from datetime import timedelta
import croniter
import json
import logging
import uuid
import binascii
from flask import request
from config import LOCATIONURL, SUBSCRIPTIONURL, USERINFOURL, TOKEN, USERFROMMOBILEURL
from data import OrderData
from data import VerificationItemData
from lib.utils import make_api_call, get_intersection_of_lists
from src.sqlalchemydb import CouponsAlchemyDB
from vouchers import Vouchers, VoucherTransactionLog
from rule import Rule, RuleCriteria, Benefits
from src.enums import *
from lib import cache
from src.rules.constants import GROCERY_ITEM_KEY, GROCERY_LOCATION_KEY, GROCERY_CACHE_TTL

logger = logging.getLogger(__name__)


def get_rule(rule_id):
    rule = Rule.find_one(rule_id)
    if rule:
        return rule
    return None


def is_between(now, date1, date2):
    if now > date2 or now < date1:
        return False
    return True


def get_num_from_str(str):
    try:
        if len(str) is 0 or str is None:
            return 0
        else:
            return int(str)
    except Exception as exp:
        return 0


def get_voucher(voucher_code):
    voucher = Vouchers.find_one(voucher_code)
    now = datetime.datetime.utcnow()
    if voucher and voucher.from_date <= now <= voucher.to_date:
        if voucher.schedule:
            for schedule in voucher.schedule:
                if schedule['type'] is SchedulerType.exact.value:
                    scheduled_time_start = datetime.datetime.strptime(schedule['value'],"%Y-%m-%d %H:%M:%S.%f")
                    weeks, days, hours, minutes, seconds = tuple(schedule['duration'].split(':'))
                    scheduled_time_end = scheduled_time_start + timedelta(days=get_num_from_str(days), weeks=get_num_from_str(weeks), hours=get_num_from_str(hours), minutes=get_num_from_str(minutes), seconds=get_num_from_str(seconds))
                    if is_between(now, scheduled_time_start, scheduled_time_end):
                        return voucher, None
                elif schedule['type'] is SchedulerType.daily.value:
                    hours, minutes, seconds = tuple(schedule['value'].split(':'))
                    today = datetime.datetime.utcnow().date()
                    justtime = datetime.time(hour=get_num_from_str(hours), minute=get_num_from_str(minutes), second=get_num_from_str(seconds))
                    scheduled_time_start = datetime.datetime.combine(today, justtime)
                    weeks, days, hours, minutes, seconds = tuple(schedule['duration'].split(':'))
                    scheduled_time_end = scheduled_time_start + timedelta(days=get_num_from_str(days), weeks=get_num_from_str(weeks), hours=get_num_from_str(hours), minutes=get_num_from_str(minutes), seconds=get_num_from_str(seconds))
                    if is_between(now, scheduled_time_start, scheduled_time_end):
                        return voucher, None
                elif schedule['type'] is SchedulerType.cron.value:
                    cron = croniter.croniter(schedule['value'], now)
                    cron_prev = cron.get_prev(datetime.datetime)
                    cron_current = cron.get_current(datetime.datetime)
                    cron_next = cron.get_next(datetime.datetime)
                    weeks, days, hours, minutes, seconds = tuple(schedule['duration'].split(':'))
                    deltatime = timedelta(days=get_num_from_str(days), weeks=get_num_from_str(weeks),
                                                          hours=get_num_from_str(hours), minutes=get_num_from_str(minutes),
                                                          seconds=get_num_from_str(seconds))
                    duration_prev = cron_prev + deltatime
                    duration_current = cron_current + deltatime
                    duration_next = cron_next + deltatime
                    if is_between(now, cron_prev, duration_prev) or \
                            is_between(now, cron_current, duration_current) or \
                            is_between(now, cron_next, duration_next):
                        return voucher, None
            return None, u'The voucher {} is not valid'.format(voucher.code)
        return voucher, None
    elif voucher and now > voucher.to_date:
        voucher.delete()
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
                    for item in order.items:
                        if item.subscription_id in subscription_id_list:
                            item_discount = (item.quantity * item.price * discount)/total
                            products_dict[item.subscription_id]['discount'] = max(
                                products_dict[item.subscription_id]['discount'], item_discount)
                benefit_dict['couponCode'] = existing_voucher['voucher'].code
                benefit_dict['discount'] = discount
                benefit_dict['freebies'] = freebie_list
                benefit_dict['items'] = subscription_id_list
                benefit_dict['type'] = existing_voucher['voucher'].type
                benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
                benefit_dict['channel'] = [Channels(c).value for c in rule.criteria_obj.channels]
                benefit_dict['custom'] = existing_voucher['voucher'].custom
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
        product_dict['discount'] = round(product_dict['discount'], 2)

    total_discount = round(total_discount, 2)
    response_dict = dict()

    response_dict['products'] = products_list
    response_dict['benefits'] = benefits_list
    response_dict['totalDiscount'] = total_discount
    response_dict['paymentMode'] = payment_modes_list
    response_dict['channel'] = channels_list
    response_dict['couponCodes'] = [existing_voucher['voucher'].code for existing_voucher in order.existing_vouchers]
    return response_dict


def get_benefits_new(order):
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
                flat_discount = 0.0
                percentage_discount = 0.0
                percentage_discount_actual = 0.0
                freebie_list = list()
                benefit_type = BenefitType(benefit['type'])
                if benefit_type is BenefitType.freebie:
                    freebie_list.append(benefit['value'])
                else:
                    if benefit_type is BenefitType.amount and benefit['value']:
                        flat_discount = benefit['value']
                    elif benefit_type is BenefitType.percentage and benefit['value']:
                        percentage = benefit['value']
                        percentage_discount = percentage * total / 100
                        percentage_discount_actual = percentage_discount
                    if max_discount and flat_discount > max_discount:
                        flat_discount = max_discount
                    if max_discount and percentage_discount > max_discount:
                        percentage_discount = max_discount
                    for item in order.items:
                        if item.subscription_id in subscription_id_list:
                            if flat_discount:
                                item_flat_discount = (item.quantity * item.price * flat_discount)/total
                                products_dict[item.subscription_id]['discount'] = max(
                                    products_dict[item.subscription_id]['discount'], item_flat_discount)
                            if percentage_discount:
                                item_percentage_discount = (item.quantity * item.price * percentage_discount)/total
                                products_dict[item.subscription_id]['discount'] = max(
                                    products_dict[item.subscription_id]['discount'], item_percentage_discount)
                benefit_dict['couponCode'] = existing_voucher['voucher'].code
                benefit_dict['flat_discount'] = flat_discount
                benefit_dict['prorated_discount'] = percentage_discount
                benefit_dict['prorated_discount_actual'] = percentage_discount_actual
                benefit_dict['freebies'] = freebie_list
                benefit_dict['items'] = subscription_id_list
                benefit_dict['type'] = existing_voucher['voucher'].type
                benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
                benefit_dict['channel'] = [Channels(c).value for c in rule.criteria_obj.channels]
                benefit_dict['custom'] = existing_voucher['voucher'].custom
                if max_discount:
                    benefit_dict['max_discount'] = max_discount
                else:
                    benefit_dict['max_discount'] = None
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
        product_dict['discount'] = round(product_dict['discount'], 2)

    for a_benefit in benefits_list:
        a_benefit['prorated_discount'] = a_benefit['prorated_discount_actual']
        del a_benefit['prorated_discount_actual']

    total_discount = round(total_discount, 2)
    response_dict = dict()

    response_dict['products'] = products_list
    response_dict['benefits'] = benefits_list
    response_dict['totalDiscount'] = total_discount
    response_dict['paymentMode'] = payment_modes_list
    response_dict['channel'] = channels_list
    response_dict['couponCodes'] = [existing_voucher['voucher'].code for existing_voucher in order.existing_vouchers]
    return response_dict


def apply_benefits(args, order, benefits):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    voucher_id_list = list()
    db = CouponsAlchemyDB()
    db.begin()
    try:
        for existing_voucher in order.existing_vouchers:
            voucher_id = existing_voucher['voucher'].id
            if voucher_id in voucher_id_list:
                continue
            voucher_id_list.append(voucher_id)
            rule = existing_voucher['voucher'].rules_list[0]
            status = rule.check_usage(order.customer_id, existing_voucher['voucher'].id_bin, db)
            if not status.get('success', False):
                db.rollback()
                return False, 400, u'Voucher {} has expired'.format(existing_voucher['voucher'].code)
            transaction_log = VoucherTransactionLog(**{
                'id': uuid.uuid1().hex,
                'user_id': user_id,
                'voucher_id': voucher_id,
                'order_id': order_id,
                'status': VoucherTransactionStatus.in_progress.value,
                'response': json.dumps(benefits)
            })
            transaction_log.save(db)
        db.commit()
    except Exception as e:
        logger.exception(e)
        db.rollback()
        return False, 500, u'Unknown Error. Please try after some time'
    # else:
    #     db.commit()
    return True, 200, None


def get_user_details(response):
    # returns the order no of the user
    try:
        data_list = json.loads(response.text)
        if not data_list:
            return False, None, u'User Does not exist'
        return True, data_list[0]['ordercount'], None
    except Exception as e:
        logger.exception(e)
        return False, None, u'Unable to fetch User details'



def fetch_items(item_id_list, item_to_quantity):
    cached_item_list = list()
    to_fetch_item_list = list()
    for item_id in item_id_list:
        key = GROCERY_ITEM_KEY + u'{}'.format(item_id)
        obj = cache.get(key)
        if obj:
            cached_item_list.append(obj)
        else:
            to_fetch_item_list.append(item_id)

    for item in cached_item_list:
        item.quantity = item_to_quantity[item.subscription_id]
    if to_fetch_item_list:
        item_id_list_str = ','.join(u'{}'.format(v) for v in to_fetch_item_list)

        item_url = SUBSCRIPTIONURL + item_id_list_str + '/'

        headers = {
            'Authorization': TOKEN
        }

        list_of_responses = make_api_call([item_url], headers=headers)

        response = list_of_responses[0]

        try:
            data_list = json.loads(response.text)
        except Exception as e:
            logger.exception(e)
            return False, None, u'Unable to fetch Items'

        if not isinstance(data_list, list) or len(data_list) != len(to_fetch_item_list):
            return False, None, u'Invalid Item ids provided'

        for data in data_list:
            item_dict = dict()
            item_dict['brand'] = data.get('brandid')
            item_dict['category'] = [data.get('categoryid')]
            item_dict['product'] = [data.get('productid')]
            item_dict['seller'] = data.get('sellerid')
            item_dict['storefront'] = data.get('storefront')
            item_dict['variant'] = data.get('variantid')
            item_dict['price'] = data.get('offerprice')
            item_dict['quantity'] = item_to_quantity[data.get('itemid')]
            item_dict['subscription_id'] = data.get('itemid')
            item_obj = VerificationItemData(**item_dict)
            key = GROCERY_ITEM_KEY + u'{}'.format(data.get('itemid'))
            cache.set(key, item_obj, ex=GROCERY_CACHE_TTL)
            cached_item_list.append(item_obj)

    return True, cached_item_list, None


def fetch_location_dict(area_id):
    key = GROCERY_LOCATION_KEY+u'{}'.format(area_id)
    location_dict = cache.get(key)
    if not location_dict:
        location_url = LOCATIONURL + str(area_id) + '/'
        headers = {
            'Authorization': TOKEN
        }
        response_list = make_api_call([location_url], headers=headers)
        response = response_list[0]
        try:
            data_list = json.loads(response.text)
        except Exception as e:
            logger.exception(e)
            return False, None, u'Unable to fetch area details'

        if not data_list:
            return False, None, u'Area Does not exist'

        data = data_list[0]
        location_dict = dict()
        location_dict['area'] = data.get('areaid')
        location_dict['country'] = [data.get('countryid')]
        location_dict['state'] = [data.get('stateid')]
        location_dict['city'] = [data.get('cityid')]
        location_dict['zone'] = [data.get('zoneid')]

        cache.set(key, location_dict, ex=GROCERY_CACHE_TTL)

    return True, location_dict, None


def fetch_user_details(customer_id):
    if u'{}'.format(request.url_rule) == u'/vouchers/v1/check' or \
                    u'{}'.format(request.url_rule) == u'/vouchers/v1/apply':
        user_info_url = USERINFOURL + str(customer_id) + '/'
    else:
        user_info_url = USERFROMMOBILEURL + str(customer_id) + '/'
    headers = {
        'Authorization': TOKEN
    }
    response_list = make_api_call([user_info_url], headers=headers)
    response = response_list[0]
    return get_user_details(response)


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

    success, items, error = fetch_items(item_id_list, item_to_quantity)
    if not success:
        return False, None, error

    success, location_dict, error = fetch_location_dict(area_id)
    if not success:
        return False, None, error

    success, order_no, error = fetch_user_details(customer_id)
    if not success:
        return False, None, error

    order_no += 1
    order_data_dict = dict()
    order_data_dict['order_no'] = order_no
    order_data_dict.update(location_dict)
    order_data_dict['channel'] = args.get('channel')
    order_data_dict['source'] = args.get('source')
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
    kwargs['schedule'] = data.get('schedule')
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
        'location.city', 'location.area', 'location.zone', 'source'
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
        sql = 'select  v.*,a.`type`, a.`variants`, a.`zone`  from `vouchers` v join (select * from `auto_freebie_search` where (type = :type and zone in :zone and ('+where_clause+') and (cart_range_min is null or cart_range_min <= :ordertotal) and (cart_range_max is null or cart_range_max >= :ordertotal) and :now > `from` and :now < `to`)) a on v.id=a.`voucher_id`'
    else:
        for item in order.items:
            item_list.append(item.subscription_id)
        params = dict()
        sql = 'select v.*,a.`type`, a.`variants`, a.`zone` from `vouchers` v join (select * from `auto_freebie_search` where (type = :type and zone in :zone and (cart_range_min is null or cart_range_min <= :ordertotal) and (cart_range_max is null or cart_range_max >= :ordertotal) and :now > `from` and :now < `to`)) a on v.id=a.`voucher_id`'
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


def fetch_order_response(args):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    db = CouponsAlchemyDB()
    result = db.find("voucher_use_tracker", **{'order_id': order_id, 'user_id': user_id})
    if result:
        # result may have one entry per voucher,
        # but all entries will have same json for an order id,
        # Hence its safe accessing the list's 0th element
        return True, json.loads(result[0]['response'])
    return False, None


def save_auto_freebie_from_voucher(voucher, db=None):
    voucher.get_rule(db)
    if voucher.type is not VoucherType.regular_coupon.value:
        auto_freebie_values = dict()
        auto_freebie_values['type'] = voucher.type
        auto_freebie_values['zone'] = voucher.rules_list[0].criteria_obj.zone[0],
        auto_freebie_values['range_min'] = voucher.rules_list[0].criteria_obj.range_min
        auto_freebie_values['range_max'] = voucher.rules_list[0].criteria_obj.range_max
        auto_freebie_values['cart_range_min'] = voucher.rules_list[0].criteria_obj.cart_range_min
        auto_freebie_values['cart_range_max'] = voucher.rules_list[0].criteria_obj.cart_range_max
        auto_freebie_values['voucher_id'] = binascii.a2b_hex(voucher.id)
        if voucher.type is VoucherType.auto_freebie.value:
            auto_freebie_values['variants'] = voucher.rules_list[0].criteria_obj.variants[0]
        else:
            auto_freebie_values['variants'] = None
        auto_freebie_values['from'] = voucher.from_date
        auto_freebie_values['to'] = voucher.to_date
        if not db:
            db = CouponsAlchemyDB()
        db.insert_row("auto_freebie_search", **auto_freebie_values)


def save_auto_freebie_from_voucher_dict(voucher_dict):
    voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
    vouchers = Vouchers(**voucher_dict)
    save_auto_freebie_from_voucher(vouchers)


def find_overlapping_vouchers(existing_voucher_dict, db=None):
    sql = 'select * from `auto_freebie_search` where type=:type and zone=:zone and ('

    if existing_voucher_dict.get('cart_range_min'):
        where_clause1 = '( ((cart_range_min is null or (:cart_range_min >= cart_range_min)) && (cart_range_max is null or (:cart_range_min <= cart_range_max))) or ( (:cart_range_min is null or (cart_range_min >= :cart_range_min)) && (:cart_range_max is null or (cart_range_min <= :cart_range_max))) ) '
    else:
        where_clause1 = '(cart_range_min is null)'
    if existing_voucher_dict.get('cart_range_max'):
        where_clause2 = '( ((cart_range_min is null or (:cart_range_max >= cart_range_min)) && (cart_range_max is null or (:cart_range_max <= cart_range_max)) ) or ( (:cart_range_min is null or (cart_range_max >= :cart_range_min)) && (:cart_range_max is null or (cart_range_max <= :cart_range_max))) )'
    else:
        where_clause2 = '(cart_range_max is null)'

    date_overlapping_caluse = '(((:from >= `from` && :from <= `to`) or (:to >= `from` && :to <= `to`)) or ((`from` >= :from && `from` <= :to) or (`to` >= :from && `to` <= :to) ))'

    if existing_voucher_dict.get('type') is VoucherType.auto_freebie.value:
        if existing_voucher_dict.get('range_min'):
            where_clause3 = '( ((range_min is null or (:range_min >= range_min)) && (range_max is null or (:range_min <= range_max))) or ( (:range_min is null or (range_min >= :range_min)) && (:range_max is null or (range_min <= :range_max))) )'
        else:
            where_clause3 = '(range_min is null)'
        if existing_voucher_dict.get('range_max'):
            where_clause4 = '( ((range_min is null or (:range_max >= range_min)) && (range_max is null or (:range_max <= range_max)) ) or ( (:range_min is null or (range_max >= :range_min)) && (:range_max is null or (range_max <= :range_max))) )'
        else:
            where_clause4 = '(range_max is null)'

        sql += '(' + where_clause1 + ' or ' + where_clause2 + ' or ' + where_clause3 +\
               ' or ' + where_clause4 + ') && ('+date_overlapping_caluse+')' + ') and variants=:variants'
    else:
        sql += '(' + where_clause1 + ' or ' + where_clause2 + ') && ('+date_overlapping_caluse+')' + ')'

    if not db:
        db = CouponsAlchemyDB()
    existing_voucher_list = db.execute_raw_sql(sql, existing_voucher_dict)
    if existing_voucher_list:
        error_list = list()
        for existing_voucher in existing_voucher_list:
            voucher = Vouchers.find_one_by_id(existing_voucher['voucher_id'])
            if voucher.code != existing_voucher_dict.get('code'):
                msg = u'Voucher {} overlaps ranges with this voucher with values cart_range_min: {}, cart_range_max: {}'.format(
                    voucher.code, existing_voucher['cart_range_min'], existing_voucher['cart_range_max'])
                if existing_voucher_dict.get('type'):
                    msg += u', range_min: {}, range_max: {}'.format(existing_voucher['range_min'], existing_voucher['range_max'])
                error_list.append(msg)
                continue
            error_list.append(u'Expire the voucher {} and recreate'.format(voucher.code))
        if error_list:
            return False, error_list

    return True, None
