import binascii
import datetime
import json
import logging
import copy
from flask import request
from constants import GROCERY_ITEM_KEY, GROCERY_CACHE_TTL, GROCERY_LOCATION_KEY
import config
from data import VerificationItemData, OrderData
from lib import cache
from lib.utils import make_api_call, create_success_response
from src.enums import VoucherType, BenefitType
from src.rules.rule import Benefits
from src.rules.utils import create_rule_object, save_vouchers, create_regular_voucher
from src.rules.vouchers import Vouchers
from src.sqlalchemydb import CouponsAlchemyDB

logger = logging.getLogger(__name__)


def create_freebie_coupon(args):
    # code must have only 1 element and it has been validated before
    # hence safe in accessing directly 0th element
    # in case of update, delete the voucher, delete entry from auto_benefits
    # create a new rule and create a new voucher on the created rule, and an entry in auto_benefits
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
        'benefits': [
            {
                'type': 2,
                'freebies': rule.get('benefits')[0].get('freebies'),
            }
        ],
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

    rule_obj = create_rule_object(data, args.get('user_id'), get_criteria_kwargs)
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
        db.insert_row("auto_benefits", **auto_freebie_values)

    for s in success_list:
        del s['id']
    return True, success_list, error_list


def create_regular_coupon(args):
    return create_regular_voucher(args, get_criteria_kwargs)


def generate_auto_freebie():
    db = CouponsAlchemyDB()
    db.delete_row("auto_benefits")
    voucher_list = db.find("vouchers")
    for voucher in voucher_list:
        save_auto_freebie_from_voucher_dict(voucher)


def get_user_details(response):
    # returns the order no of the user
    try:
        data = json.loads(response.text)
        if not data:
            return False, None, u'User Does not exist'
        return True, data['data']['count'], None
    except Exception as e:
        logger.exception(e)
        return False, None, u'Unable to fetch User details'


def fetch_items(subscription_id_list, item_map):
    # item_map is a subscription id to a list dicts of item ids and their resp quantities
    # we must cache subscription id to subscription dict and fetch the rest from the api
    # and set the cache for them.
    # While iterating over subscription ids, build the list of verification item dicts
    # and create the item and add it to final resultant list.
    item_list = list()
    to_fetch_subscription_list = list()
    for subscription_id in subscription_id_list:
        key = GROCERY_ITEM_KEY + u'{}'.format(subscription_id)
        subscription_dict = cache.get(key)
        if subscription_dict:
            for item in item_map.get(subscription_id):
                item_id = item.get('item_id')
                quantity = item.get('quantity')
                item_dict = copy.deepcopy(subscription_dict)
                item_dict['quantity'] = quantity
                item_dict['subscription_id'] = subscription_id
                item_dict['item_id'] = item_id
                item_obj = VerificationItemData(**item_dict)
                item_list.append(item_obj)
        else:
            to_fetch_subscription_list.append(subscription_id)

    if to_fetch_subscription_list:
        to_fetch_subscription_list = [int(to_fetch_item_id) for to_fetch_item_id in to_fetch_subscription_list]

        body = {
            "query": {
                "type": ["grocery"],
                "filters": {
                    "id": to_fetch_subscription_list
                },
                "select": ["sellerId", "variantId", "productId", "categories", "storeFronts", "brandId"]
            },
            "count": len(to_fetch_subscription_list),
            "offset": 0
        }

        headers = config.SUBSCRIPTIONHEADERS

        response = make_api_call(config.SUBSCRIPTIONURL, method='POST', headers=headers, body=body)

        try:
            response_data = json.loads(response.text)
        except Exception as e:
            logger.exception(e)
            return False, None, u'Unable to fetch Items'

        try:
            count = response_data['results'][0]['items'][0]['count']
            if count != len(to_fetch_subscription_list):
                return False, None, u'Invalid Subscription Ids provided'
            raw_data_list = response_data['results'][0]['items'][0]['items']
        except Exception as e:
            logger.exception(e)
            logger.error(u'Invalid Response for items {} recieved {}'.format(to_fetch_subscription_list, response_data))
            return False, None, u'Unknown Error. Please contact tech support'

        for raw_data in raw_data_list:
            data = {
                'variant': raw_data['variantId'],
                'price': raw_data['offerPrice'],
                'brand': raw_data['brandId'],
                'product': [raw_data['productId']],
                'seller': raw_data['sellerId']
            }
            category_list = list()
            for category in raw_data['categories']:
                category_list.append(category['id'])
            data['category'] = category_list
            storefront_list = list()
            for storefront in raw_data['storeFronts']:
                storefront_list.append(storefront['id'])
            data['storefront'] = storefront_list
            key = GROCERY_ITEM_KEY + u'{}'.format(raw_data.get('id'))
            cache.set(key, data, ex=GROCERY_CACHE_TTL)
            for item in item_map.get(u'{}'.format(raw_data.get('id'))):
                item_id = item.get('item_id')
                quantity = item.get('quantity')
                item_dict = copy.deepcopy(data)
                item_dict['quantity'] = quantity
                item_dict['subscription_id'] = raw_data.get('id')
                item_dict['item_id'] = item_id
                item_obj = VerificationItemData(**item_dict)
                item_list.append(item_obj)

    return True, item_list, None


def fetch_location_dict(id):
    key = GROCERY_LOCATION_KEY+u'{}'.format(id)
    location_dict = cache.get(key)
    if not location_dict:
        location_url = config.LOCATIONURL + str(id)
        response = make_api_call(location_url)

        try:
            raw_data = json.loads(response.text)
        except Exception as e:
            logger.exception(e)
            return False, None, u'Unable to fetch details for geo id={}'.format(id)

        if not raw_data.get('locations'):
            return False, None, u'geo id={} does not exist'.format(id)

        locations = raw_data.get('locations')

        data = None
        for location in locations:
            if 'tags' in location and location['tags']:
                if 'grocery' in location['tags']:
                    data = location
                    break

        if not data and not (('tags' in locations[0]) and locations[0]['tags'] and ('grocery' not in locations[0]['tags'])):
            data = locations[0]

        if not data or not data['types']:
            return False, None, u'{} is not a valid geo Id'.format(id)

        geo_types_ordered = ['area', 'pincode', 'zone', 'city', 'state']
        id_types = data['types']
        id_type = None
        for geo_type in geo_types_ordered:
            if geo_type in id_types:
                id_type = geo_type
                break

        if not id_type:
            return False, None, u'{} is not a valid geo Id'.format(id)

        location_dict = {
            'area': list(),
            'state': list(),
            'city': list(),
            'pincode': list(),
            'zone': list()
        }
        for container in data.get('containers'):
            for geo_type in geo_types_ordered:
                if geo_type in container['types']:
                    location_dict[geo_type].append(container['gid'])
        location_dict[id_type].append(id)

        cache.set(key, location_dict, ex=GROCERY_CACHE_TTL)

    return True, location_dict, None


def fetch_order_detail(args):
    # custom implementation for askmegrocery, this method has to be
    # re-written to integrate with other sites' services
    # This
    geo_id = args.get('geo_id', None)
    subscription_id_set = set()
    item_map = dict()

    for item in args.get('products', list()):
        subscription_id_set.add(item.get('subscription_id'))
        item_dict = {
            'item_id': item.get('item_id'),
            'quantity': item.get('quantity')
        }
        subscription_to_item_list = item_map.get(item.get('subscription_id'), list())
        subscription_to_item_list.append(item_dict)
        item_map[item.get('subscription_id')] = subscription_to_item_list

    success, items, error = fetch_items(list(subscription_id_set), item_map)
    if not success:
        return False, None, [error]

    success, location_dict, error = fetch_location_dict(geo_id)
    if not success:
        return False, None, [error]

    order_data_dict = dict()
    order_data_dict.update(location_dict)
    order_data_dict['channel'] = args.get('channel')
    order_data_dict['source'] = args.get('source')
    order_data_dict['payment_mode'] = args.get('payment_mode')
    order_data_dict['check_payment_mode'] = args.get('check_payment_mode')
    order_data_dict['items'] = items
    order_data_dict['customer_id'] = args.get('customer_id')
    order_data_dict['session_id'] = args.get('session_id')
    order_data_dict['order_id'] = args.get('order_id')
    order_data_dict['geo_id'] = args.get('geo_id')
    order_data_dict['validate'] = args.get('validate', True)
    order_data = OrderData(**order_data_dict)
    return True, order_data, None


def get_criteria_kwargs(data):
    criteria = data.get('criteria')
    blacklist_criteria = data.get('blacklist_criteria', dict())
    benefits = data.get('benefits')
    rule_criteria_kwargs = dict()
    rule_blacklist_criteria_kwargs = dict()
    rule_criteria_keys = [
        'brands', 'categories', 'channels', 'valid_on_order_no',
        'payment_modes', 'products', 'range_max', 'cart_range_min',
        'range_min', 'sellers', 'storefronts', 'cart_range_max',
        'no_of_uses_allowed_per_user', 'no_of_total_uses_allowed',
        'variants', 'location.state',
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
    from rule_criteria import RuleCriteria
    rule_criteria = RuleCriteria(**rule_criteria_kwargs)
    rule_blacklist_criteria = RuleCriteria(**rule_blacklist_criteria_kwargs)

    benefit_list = list()

    if benefits:
        for benefit in benefits:
            type = BenefitType(benefit['type'])
            if type is BenefitType.freebie:
                freebies = benefit.get('freebies', list())
                for freebie in freebies:
                    benefit_dict = dict()
                    benefit_dict['type'] = type.value
                    benefit_dict['value'] = freebie
                    benefit_list.append(benefit_dict)
            elif type in [
                BenefitType.amount,
                BenefitType.cashback_amount,
                BenefitType.agent_cashback_amount,
                BenefitType.agent_amount
            ]:
                benefit_dict = dict()
                benefit_dict['type'] = type.value
                benefit_dict['value'] = benefit['amount']
                benefit_dict['max_cap'] = benefit.get('max_cap')
                benefit_list.append(benefit_dict)
            else:
                benefit_dict = dict()
                benefit_dict['type'] = type.value
                benefit_dict['value'] = benefit['percentage']
                benefit_dict['max_cap'] = benefit.get('max_cap')
                benefit_list.append(benefit_dict)

    benefit_criteria_kwargs = {
        'data': benefit_list
    }
    benefits = Benefits(**benefit_criteria_kwargs)
    return rule_criteria, rule_blacklist_criteria, benefits


def fetch_user_details(order):
    customer_id = order.customer_id
    user_info_url = config.USERINFOURL + '?user_id=' + str(customer_id)
    response = make_api_call(user_info_url)
    return get_user_details(response)


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
        db.insert_row("auto_benefits", **auto_freebie_values)


def save_auto_freebie_from_voucher_dict(voucher_dict):
    voucher_dict['id'] = binascii.b2a_hex(voucher_dict['id'])
    vouchers = Vouchers(**voucher_dict)
    save_auto_freebie_from_voucher(vouchers)


def is_validity_period_exclusive_for_freebie_voucher_code(existing_voucher_dict, db=None):
    sql = 'select * from `auto_benefits` where type=:type and zone=:zone and ('

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
    item_variant_map = dict()
    if freebie_type is VoucherType.auto_freebie:
        for item in order.items:
            variant_total_map[item.variant] = variant_total_map.get(item.variant, 0.0) + (item.price * item.quantity)
            list_of_item_id = item_variant_map.get(item.variant, list())
            list_of_item_id.append(item.item_id)
            item_variant_map[item.variant] = list_of_item_id
        where_clause, params = get_where_clauses(variant_total_map)
        sql = 'select  v.*,a.`type`, a.`variants`, a.`zone`  from `vouchers` v join (select * from `auto_benefits` where (type = :type and zone in :zone and ('+where_clause+') and (cart_range_min is null or cart_range_min <= :ordertotal) and (cart_range_max is null or cart_range_max >= :ordertotal) and :now > `from` and :now < `to`)) a on v.id=a.`voucher_id`'
    else:
        for item in order.items:
            item_list.append(item.item_id)
        params = dict()
        sql = 'select v.*,a.`type`, a.`variants`, a.`zone` from `vouchers` v join (select * from `auto_benefits` where (type = :type and zone in :zone and (cart_range_min is null or cart_range_min <= :ordertotal) and (cart_range_max is null or cart_range_max >= :ordertotal) and :now > `from` and :now < `to`)) a on v.id=a.`voucher_id`'
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
            success_dict['item_id_list'] = item_variant_map[voucher_dict['variants']]
        else:
            success_dict['total'] = order.total_price
            success_dict['item_id_list'] = item_list
        order.existing_vouchers.append(success_dict)


def fetch_coupon(args):
    success_list = list()
    error_list = list()
    coupon_codes = args.get('coupon_codes')
    for coupon_code in coupon_codes:
        voucher_list = Vouchers.find_all_by_code(coupon_code)
        if not voucher_list:
            error_dict = {
                'code': coupon_code,
                'error': u'Voucher code {} not found'.format(coupon_code)
            }
            error_list.append(error_dict)
            continue
        for voucher in voucher_list:
            voucher_dict = dict()
            rules = list()
            voucher.get_rule()
            for rule in voucher.rules_list:
                criteria_obj = rule.criteria_obj
                rule_dict = dict()
                criteria = dict()
                benefits = dict()
                location_dict = dict()
                rule_dict['description'] = rule.description
                criteria['no_of_uses_allowed_per_user'] = criteria_obj.usage['no_of_uses_allowed_per_user']
                criteria['no_of_total_uses_allowed'] = criteria_obj.usage['no_of_total_uses_allowed']
                criteria['range_min'] = criteria_obj.range_min
                criteria['range_max'] = criteria_obj.range_max
                criteria['cart_range_min'] = criteria_obj.cart_range_min
                criteria['cart_range_max'] = criteria_obj.cart_range_max
                criteria['channels'] = criteria_obj.channels
                criteria['brands'] = criteria_obj.brands
                criteria['products'] = criteria_obj.products
                criteria['categories'] = criteria_obj.categories
                criteria['storefronts'] = criteria_obj.storefronts
                criteria['variants'] = criteria_obj.variants
                criteria['sellers'] = criteria_obj.sellers
                location_dict['country'] = criteria_obj.country
                location_dict['state'] = criteria_obj.state
                location_dict['city'] = criteria_obj.city
                location_dict['area'] = criteria_obj.area
                location_dict['zone'] = criteria_obj.zone
                criteria['location'] = location_dict
                criteria['valid_on_order_no'] = criteria_obj.valid_on_order_no
                criteria['payment_modes'] = criteria_obj.payment_modes
                benefits_obj = rule.benefits_obj
                # benefits['max_discount'] = benefits_obj.max_discount
                for data in benefits_obj.data:
                    type = BenefitType(data.get('type'))
                    if type in [
                        BenefitType.amount,
                        BenefitType.agent_amount,
                        BenefitType.cashback_amount,
                        BenefitType.agent_cashback_amount
                    ]:
                        benefits['amount'] = data.get('value')
                    elif type in [
                        BenefitType.percentage,
                        BenefitType.agent_percentage,
                        BenefitType.cashback_percentage,
                        BenefitType.agent_cashback_percentage
                    ]:
                        benefits['percentage'] = data.get('value')
                        benefits['max_cap'] = data.get('max_cap')
                    else:
                        benefits['freebies'] = [data.get('value')]
                if not benefits.get('freebies'):
                    benefits['freebies'] = [[]]
                rule_dict['criteria'] = criteria
                rule_dict['benefits'] = benefits
                rules.append(rule_dict)
            voucher_dict['rules'] = rules
            voucher_dict['description'] = voucher.description
            voucher_dict['from'] = voucher.from_date.isoformat()
            voucher_dict['to'] = voucher.to_date.isoformat()
            voucher_dict['code'] = voucher.code
            voucher_dict['user_id'] = voucher.created_by
            voucher_dict['type'] = voucher.type
            voucher_dict['custom'] = voucher.custom
            voucher_dict['schedule'] = voucher.schedule
            success_list.append(voucher_dict)
    return create_success_response(success_list, error_list)


def create_failed_api_response(args, error_list):
    products = list()
    for product in args.get('products'):
        product_dict = dict()
        product_dict['itemid'] = product.get('item_id')
        product_dict['quantity'] = product.get('quantity')
        product_dict['discount'] = 0.0
        products.append(product_dict)
    rv = {
        'success': False,
        'error': {
            'code': 503,
            'error': ','.join(error_list)
        },
        'products': products,
        'freebies': [],
        'totalDiscount': 0.0,
        'channel': [],
        'paymentModes': [],
        'errors': error_list
    }
    return rv


def fetch_phone_no(user_id):
    url = config.USERPHONENOAPI + str(user_id)
    headers = config.USERPHONENOAPIHEADERS
    response = make_api_call(url=url, method='GET', headers=headers)
    if response.status_code != 200:
        return False, None
    try:
        data = json.loads(response.text)
        value_list = data.get('contact', dict()).get('data')
        if not value_list:
            return False, None
        for value in value_list:
            if value.get('type') == 'phone':
                if value.get('verified') == True:
                    return True, value.get('value')
                return False, value.get('value')
    except Exception as e:
        logger.exception(e)
    return False, None


def fetch_phone_no_from_session_id(session_id):
    url = config.SESSIONPHONEAPI + str(session_id)
    headers = config.USERPHONENOAPIHEADERS
    response = make_api_call(url=url, method='GET', headers=headers)
    if response.status_code != 200:
        return False, None
    try:
        data = json.loads(response.text)
        if 'result' in data and data['result'] == 'failure':
            return False, None
        if 'error' in data:
            return False, None
        return data['user']['is_phone_verified'], data['user']['phone']
    except Exception as e:
        logger.exception(e)
    return False, None
