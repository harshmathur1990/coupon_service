import binascii
import datetime
import json
import logging

from flask import request

from api.v1.data import VerificationItemData, OrderData
from api.v1.rule_criteria import RuleCriteria
from config import SUBSCRIPTIONURL, TOKEN, LOCATIONURL, USERINFOURL, USERFROMMOBILEURL
from lib import cache
from lib.utils import make_api_call
from src.enums import VoucherType, BenefitType
from src.rules.constants import GROCERY_ITEM_KEY, GROCERY_CACHE_TTL, GROCERY_LOCATION_KEY
from src.rules.rule import Benefits
from src.rules.utils import create_rule_object, save_vouchers
from src.rules.vouchers import Vouchers
from src.sqlalchemydb import CouponsAlchemyDB

logger = logging.getLogger(__name__)


def create_freebie_coupon(args):
    # code must have only 1 element and it has been validated before
    # hence safe in accessing directly 0th element
    # in case of update, delete the voucher, delete entry from auto_freebie_search
    # create a new rule and create a new voucher on the created rule, and an entry in auto_freebie_search
    # Also it is ensured that at a time only one entry per zone, spending range and category can be there.
    # Currently Scheduling is not supported in Freebies

    if args.get('schedule'):
        return False, None, [u'Scheduling is not supported in Freebie Coupons']

    code = args.get('code')[0]
    rule = args.get('rules')[0]
    criteria = rule.get('criteria')
    existing_voucher_dict = {
        'type': args.get('type'),
        'zone': criteria.get('location').get('zone')[0],
        'range_min': criteria.get('range_min'),
        'range_max': criteria.get('range_max'),
        'cart_range_min': criteria.get('cart_range_min'),
        'cart_range_max': criteria.get('cart_range_max'),
        'from': args.get('from'),
        'to': args.get('to'),
        'code': code
    }
    data = {
        'criteria': {
            'categories': {
                'in': [],
                'not_in': []
            },
            'no_of_uses_allowed_per_user': criteria.get('no_of_uses_allowed_per_user'),
            'no_of_total_uses_allowed': criteria.get('no_of_total_uses_allowed'),
            'valid_on_order_no': criteria.get('valid_on_order_no'),
            'location': {
                'country': [],
                'state': [],
                'area': [],
                'city': [],
                'zone': criteria.get('location').get('zone')
            },
            'range_min': criteria.get('range_min'),
            'range_max': criteria.get('range_max'),
            'cart_range_min': criteria.get('cart_range_min'),
            'cart_range_max': criteria.get('cart_range_max'),
            'channels': [],
            'brands': [],
            'products': {
                'in': [],
                'not_in': []
            },
            'storefronts': [],
            'sellers': [],
            'payment_modes': []
        },
        'benefits': {
            'freebies': rule.get('benefits').get('freebies'),
            'amount': None,
            'percentage': None,
            'max_discount': None
        },
        'description': rule.get('description')
    }
    if args.get('type') is VoucherType.auto_freebie.value:
        existing_voucher_dict['variants'] = criteria.get('variants')[0]
        data['criteria']['variants'] = criteria.get('variants')
    else:
        existing_voucher_dict['variants'] = None
        data['criteria']['variants'] = []

    success, error_list = is_validity_period_exclusive_for_freebie_voucher_code(existing_voucher_dict)
    if not success:
        return False, None, error_list

    rule_obj = create_rule_object(data, args.get('user_id'))
    rule_obj.save()
    success_list, error_list = save_vouchers(args, [rule_obj.id])
    if not error_list:
        voucher_id = success_list[0]['id']
        auto_freebie_values = dict()
        auto_freebie_values['type'] = args.get('type')
        auto_freebie_values['zone'] = criteria.get('location').get('zone')[0],
        auto_freebie_values['range_min'] = criteria.get('range_min')
        auto_freebie_values['range_max'] = criteria.get('range_max')
        auto_freebie_values['cart_range_min'] = criteria.get('cart_range_min')
        auto_freebie_values['cart_range_max'] = criteria.get('cart_range_max')
        auto_freebie_values['voucher_id'] = binascii.a2b_hex(voucher_id)
        auto_freebie_values['variants'] = existing_voucher_dict['variants']
        auto_freebie_values['from'] = args.get('from')
        auto_freebie_values['to'] = args.get('to')
        db = CouponsAlchemyDB()
        db.insert_row("auto_freebie_search", **auto_freebie_values)

    for s in success_list:
        del s['id']
    return True, success_list, error_list


def generate_auto_freebie():
    db = CouponsAlchemyDB()
    db.delete_row("auto_freebie_search")
    voucher_list = db.find("vouchers")
    for voucher in voucher_list:
        save_auto_freebie_from_voucher_dict(voucher)


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


def get_criteria_kwargs(data):
    criteria = data.get('criteria')
    blacklist_criteria = data.get('blacklist_criteria', dict())
    benefits = data.get('benefits')
    description = data.get('description')
    rule_criteria_kwargs = dict()
    rule_blacklist_criteria_kwargs = dict()
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
        if keys[0] not in criteria and keys[0] not in blacklist_criteria:
            continue
        if len(keys) == 2:
            if keys[1] not in criteria[keys[0]] and keys[1] not in blacklist_criteria.get(keys[0], dict()):
                continue
            if keys[1] in criteria[keys[0]]:
                rule_criteria_kwargs[keys[1]] = criteria.get(keys[0], dict()).get(keys[1])
            if keys[1] in blacklist_criteria.get(keys[0], dict()):
                if blacklist_criteria.get(keys[0], dict()).get(keys[1]):
                    rule_blacklist_criteria_kwargs[keys[1]] = blacklist_criteria.get(keys[0], dict()).get(keys[1])
        else:
            rule_criteria_kwargs[keys[0]] = criteria.get(keys[0])
            if blacklist_criteria.get(keys[0]):
                rule_blacklist_criteria_kwargs[keys[0]] = blacklist_criteria.get(keys[0])

    rule_criteria = RuleCriteria(**rule_criteria_kwargs)
    rule_blacklist_criteria = RuleCriteria(**rule_blacklist_criteria_kwargs)
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
    benefit_criteria_kwargs = {
        'max_discount': benefits.get('max_discount'),
        'data': benefit_list
    }
    benefits = Benefits(**benefit_criteria_kwargs)
    return rule_criteria, rule_blacklist_criteria, benefits


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


def is_validity_period_exclusive_for_freebie_voucher_code(existing_voucher_dict, db=None):
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


def is_validity_period_exclusive_for_voucher_code(voucher, db=None):
    if not db:
        db = CouponsAlchemyDB()
    date_overlapping_caluse = '(((:from >= `from` && :from <= `to`) or (:to >= `from` && :to <= `to`)) or ((`from` >= :from && `from` <= :to) or (`to` >= :from && `to` <= :to) ))'
    date_overlap_params = {
        'from': voucher.from_date,
        'to': voucher.to_date,
        'code': voucher.code
    }
    sql = "select * from all_vouchers where code=:code && ("+date_overlapping_caluse+")"
    voucher_list = db.execute_raw_sql(sql, date_overlap_params)
    if voucher_list:
        return False, u'Vouchers with overlapping dates found for code {}'.format(voucher.code)
    return True, None


def is_validity_period_exclusive_for_freebie_vouchers(voucher, db):
    # TODO: no need to assume freebie/auto-apply coupons will have a single rule. \
    # so we should actually run a loop here to check for each rule in the voucher
    voucher.get_rule(db)
    existing_voucher_dict = {
        'type': voucher.type,
        'zone': voucher.rules_list[0].criteria_obj.zone[0],
        'range_min': voucher.rules_list[0].criteria_obj.range_min,
        'range_max': voucher.rules_list[0].criteria_obj.range_max,
        'cart_range_min': voucher.rules_list[0].criteria_obj.cart_range_min,
        'cart_range_max': voucher.rules_list[0].criteria_obj.cart_range_max,
        'from': voucher.from_date,
        'to': voucher.to_date,
        'code': voucher.code
    }
    if voucher.type is VoucherType.auto_freebie.value:
        existing_voucher_dict['variants'] = voucher.rules_list[0].criteria_obj.variants[0]
    else:
        existing_voucher_dict['variants'] = None
    return is_validity_period_exclusive_for_freebie_voucher_code(existing_voucher_dict, db)


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
        effective_voucher = Vouchers.from_dict(voucher_dict)
        effective_voucher.get_rule()
        success_dict = {
            'voucher': effective_voucher,
        }
        if freebie_type is VoucherType.auto_freebie:
            success_dict['total'] = variant_total_map[voucher_dict['variants']]
            success_dict['subscription_id_list'] = subscription_variant_map[voucher_dict['variants']]
        else:
            success_dict['total'] = order.total_price
            success_dict['subscription_id_list'] = item_list
        order.existing_vouchers.append(success_dict)