from src.sqlalchemydb import CouponsAlchemyDB
from lib.utils import make_api_call, get_intersection_of_lists
from dateutil import parser
import binascii
import canonicaljson
import importlib
from src.rules.rule import Rule, Benefits
from config import method_dict
import hashlib
import gevent
import gevent.monkey
import datetime
import json
gevent.monkey.patch_all()

def do_it_now(body, params=dict()):
    headers = {
        'X-API-USER': 'admin',
        'X-API-TOKEN': 'kuchbhi'
    }
    r = make_api_call('http://api-service04.production.askme.com:9933/vouchers/v1/update', method='POST', headers=headers, body=body, params=params)
    return r


def create_it_now(body, params=dict()):
    headers = {
        'X-API-USER': 'admin',
        'X-API-TOKEN': 'kuchbhi'
    }
    r = make_api_call('http://api-service04.production.askme.com:9933/vouchers/v1/create', method='POST', headers=headers, body=body, params=params)
    return r

def fetch_ibl(body, params=dict()):
    headers = {
        'X-API-USER': 'admin',
        'X-API-TOKEN': 'kuchbhi'
    }
    r = make_api_call('http://api-service04.production.askme.com:9933/vouchers/v1/fetchDetail', method='POST', headers=headers, body=body, params=params)
#    r = make_api_call('http://pyservice01.staging.askme.com:9933/vouchers/v1/fetchDetail', method='POST', headers=headers, body=body, params=params)
    return r

def create_ibl(body, params=dict()):
    headers = {
        'X-API-USER': 'admin',
        'X-API-TOKEN': 'kuchbhi'
    }
#    r = make_api_call('http://api-service04.production.askme.com:9933/vouchers/v1/update', method='POST', headers=headers, body=body, params=params)
    r = make_api_call('http://api-service04.production.askme.com:9933/vouchers/v1/create', method='POST', headers=headers, body=body, params=params)
    return r

def process_one_list(a_list):
        if '2016006271REP' in a_list:
            a_list.remove('2016006271REP')
        codes = [coupon['code'] for coupon in a_list]
        body = {
                "coupon_codes": codes
                }
        r = fetch_ibl(body=body)
        with open('/Users/abhi/Documents/output_ibl_fetch.log', 'a+') as f:
            f.write(r.text)
            f.close()
        if r.status_code != 200:
            return None
        resp_data = r.json()
        coupon_list = resp_data['data']['success_list']
        a_map = dict()
        for a_data in a_list:
            a_map[a_data['code']] = a_data
        coupon_map = dict()
#        print codes.__len__()
#        print coupon_list.__len__()
        for coupon in coupon_list:
#            print("\n************************\n")
#            print coupon
#            print("\n\n\n\n\n************************\n")
            found_coupon = coupon_map.get(coupon['code'])
            if not found_coupon or found_coupon['from'] < coupon['from']:
                coupon_map[coupon['code']] = coupon
#        print coupon_map.__len__()
#        print("\n\n\n\n\n************************\n***********************\n\n\n\n")
        for code, coupon in coupon_map.iteritems():
            body = coupon
            body['from'] = '2016-06-15'
            body['to'] = a_map[coupon['code']]['to']
            del body['rules'][0]['benefits']
            r = create_ibl(body=body)
            with open('/Users/abhi/Documents/output_ibl_create.log', 'a+') as f:
                f.write(r.text)
                f.close()


def recreate_ibl():
    to = '2016-06-14'
    db = CouponsAlchemyDB()
    get_voucher_query = "select code, `from`, `to` from all_vouchers where `to`> :to  and ( code rlike '20[1-5][0-9][0-9]{6}NEW'  or code rlike '20[1-5][0-9][0-9]{6}TWO' or code rlike '20[1-5][0-9][0-9]{6}REP')"
    code_from_list = db.execute_raw_sql(get_voucher_query, {'to': to})
    code_from_list = [{'to': code_from_dict['to'].isoformat(), 'from': code_from_dict['from'].isoformat(), 'code': code_from_dict['code']} for code_from_dict in code_from_list]
    print code_from_list.__len__()
    lists = list(chunks(code_from_list, 200))
#    process_one_list(lists[0])
    threads = [gevent.spawn(process_one_list, a_list) for a_list in lists]
    gevent.joinall(threads)


#    for a_list in lists:
#        gevent.spawn(process_one_list, a_list)

#        with open('/Users/abhi/Documents/output_ibl_expire.log', 'a+') as f:
#            f.write(r.text)
#            f.close()



def do_iocl_date_correction():
    to = '2016-06-14'
    db = CouponsAlchemyDB()
    get_voucher_query = "select code, `from`, `to` from all_vouchers where `to`> :to  and ( code rlike '20[1-5][0-9][0-9]{6}NEW'  or code rlike '20[1-5][0-9][0-9]{6}TWO' or code rlike '20[1-5][0-9][0-9]{6}REP')"
    code_from_list = db.execute_raw_sql(get_voucher_query, {'to': to})
    code_from_list = [{'to': code_from_dict['to'].isoformat(), 'from': code_from_dict['from'].isoformat(), 'code': code_from_dict['code']} for code_from_dict in code_from_list]
    lists = list(chunks(code_from_list, 2000))
    for a_list in lists:
        body = list()
        for coupon in a_list:
            if coupon['code'] == '2016006271REP':
                continue
            body_dict = {
                "coupons": [{
                    'code': coupon['code'],
                    'from': coupon['from']
                }],
                "update": {
                    "to": '2016-01-01'
                }
            }
            body.append(body_dict)
        r = do_it_now(body=body)
        with open('/Users/abhi/Documents/output_ibl_expire.log', 'a+') as f:
            f.write(r.text)
            f.close()


def do_date_correction():
    db = CouponsAlchemyDB()
    query = 'select count(1) c, `to` from vouchers group by `to` order by c desc'
    count_date_list = db.execute_raw_sql(query, dict())
    done_date = parser.parse("2016-08-30 18:30:00.000000")
    for count_date_map in count_date_list:
        date_value = count_date_map['to']
        if date_value == done_date:
            continue
        get_voucher_query = 'select `code`, `from` from vouchers where `to` = :to'
        code_from_list = db.execute_raw_sql(get_voucher_query, {'to': date_value})
        code_from_list = [{'from': code_from_dict['from'].isoformat(), 'code': code_from_dict['code']} for code_from_dict in code_from_list]
        lists = list(chunks(code_from_list, 5000))
        for a_list in lists:
            body = [
                {
                    "coupons": a_list,
                    "update": {
                        "to": date_value.isoformat()
                    }
                }
            ]
            r = do_it_now(body=body, params={'force': u'true'})
            with open('/var/log/couponlogs/grocery/output_date_correction.log', 'a+') as f:
                f.write(r.text)
                f.close()


def chunks(l,n):
    for i in range(0, len(l), n):
        yield l[i:i+n]


def update_is_active():
    codes_list = ["HEPYKM","HEPYLX","HEPYXB","HEQBDG"]
    lists = list(chunks(codes_list, 10000))
    for a_list in lists:
        body = [
            {
                "coupons": a_list,
                "update": {
                    "is_active": True
                }
            }
        ]
        r = do_it_now(body=body)
        with open('/Users/harshmathur/Documents/update_to_date/output_active.log', 'a+') as f:
            f.write(r.text)
            f.close()


def fix_order_no(valid_on_order_no):

    if not valid_on_order_no:
        return valid_on_order_no

    exact_order_no_list = list()
    min_order_no = None
    final_valid_on_order_no = list()
    for an_order_no in valid_on_order_no:
        try:
            # to convert order nos which are exact integers
            exact_order_no_list.append(int(an_order_no))
        except ValueError:
            # to convert order nos which are like 4+ means minimum order no 4
            try:
                new_min_order_no = int(an_order_no[:-1])
                if not min_order_no or min_order_no > new_min_order_no:
                    min_order_no = new_min_order_no
            except ValueError:
                raise ValueError

    for order_no in exact_order_no_list:
        if min_order_no:
            if order_no < min_order_no:
                final_valid_on_order_no.append(u'{}'.format(order_no))
        else:
            final_valid_on_order_no.append(u'{}'.format(order_no))

    if min_order_no and min_order_no > 1:
        final_valid_on_order_no.append(u'{}+'.format(min_order_no))

    return final_valid_on_order_no


def cleanup_rules():
    rule_criteria_class = getattr(
            importlib.import_module(
                method_dict.get('criteria_class')['package']),
            method_dict.get('criteria_class')['attribute'])
    db = CouponsAlchemyDB()
    rule_dict_list = db.find("rule")
    for rule_dict in rule_dict_list:
        rule_dict['id'] = binascii.b2a_hex(rule_dict['id'])
        rule = Rule(**rule_dict)
        criteria_dict = canonicaljson.json.loads(rule.criteria_json)
        if rule.blacklist_criteria_json:
            blacklist_dict = canonicaljson.json.loads(rule.blacklist_criteria_json)
        else:
            blacklist_dict = dict()

        all_list = ['all']

        criteria_payment_modes = criteria_dict.get('payment_modes')
        if criteria_payment_modes:
            criteria_payment_modes = [criteria_payment_mode.lower() for criteria_payment_mode in criteria_payment_modes]

        if criteria_payment_modes and get_intersection_of_lists(criteria_payment_modes, all_list):
            del criteria_dict['payment_modes']

        blacklist_criteria_payment_modes = blacklist_dict.get('payment_modes')
        if blacklist_criteria_payment_modes:
            blacklist_criteria_payment_modes = [blacklist_criteria_payment_mode.lower() for blacklist_criteria_payment_mode in blacklist_criteria_payment_modes]

        if blacklist_criteria_payment_modes and get_intersection_of_lists(blacklist_criteria_payment_modes, all_list):
            del blacklist_dict['payment_modes']
        try:
            criteria_dict['valid_on_order_no'] = fix_order_no(criteria_dict.get('valid_on_order_no'))
        except ValueError:
            success = False
            # error.append(u'Invalid value in valid_on_order_no in rule criteria')

        try:
            blacklist_dict['valid_on_order_no'] = fix_order_no(blacklist_dict.get('valid_on_order_no'))
        except ValueError:
            success = False
            # error.append(u'Invalid value in valid_on_order_no in rule blacklist criteria')
        benefit_dict = canonicaljson.json.loads(rule.benefits_json)
        rule_criteria = rule_criteria_class(**criteria_dict)
        rule_blacklist_criteria = rule_criteria_class(**blacklist_dict)
        benefits = Benefits(**benefit_dict)
        values = dict()
        values['id'] = rule.id_bin
        values['criteria_json'] = rule_criteria.canonical_json()
        values['blacklist_criteria_json'] = rule_blacklist_criteria.canonical_json()
        values['benefits_json'] = benefits.canonical_json()
        un_hashed_string = unicode(values['criteria_json']) + \
            unicode(values['criteria_json']) + unicode(values['criteria_json'])
        values['sha2hash'] = hashlib.sha256(un_hashed_string).hexdigest()
        db.update_row("rule", "id", **values)


def do_expire_iocl_and_recreate_with_valid_on_first_order():
    date_value = "2016-08-30 18:30:00.000000"
    expire_date_value = "2015-08-30 18:30:00.000000"
    expire_date = parser.parse(expire_date_value)
    date_value = parser.parse(date_value)
    db = CouponsAlchemyDB()
    get_voucher_query = 'select code, `from` from all_vouchers where `to`=:to and code not in (select av.code from all_vouchers av join `voucher_use_tracker` vut on av.id=vut.`voucher_id` where `to`=:to)'
    code_from_list = db.execute_raw_sql(get_voucher_query, {'to': date_value})
    code_from_list = [{'from': code_from_dict['from'].isoformat(), 'code': code_from_dict['code']} for code_from_dict in code_from_list]

    code_all_list = [code_from_dict['code'] for code_from_dict in code_from_list]

    lists = list(chunks(code_from_list, 5000))
    for a_list in lists:
        body = [
            {
                "coupons": a_list,
                "update": {
                    "to": expire_date.isoformat()
                }
            }
        ]
        r = do_it_now(body=body)
        with open('/var/log/couponlogs/grocery/output_iocl.log', 'a+') as f:
            f.write(r.text)
            f.close()

    codes_all_rule_list = list(chunks(code_all_list, 5000))
    for codes_for_68_rule in codes_all_rule_list:
        body = {
            "code": codes_for_68_rule,
            "from": "2016-06-18 00:00:00",
            "description": "arti-IOCL punjab",
            "rules": [
                {
                    "benefits": {
                        "amount": 250,
                        "freebies": [
                            []
                        ]
                    },
                    "description": "arti-IOCL punjab",
                    "criteria": {
                        "cart_range_min": 250,
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 1,
                        "valid_on_order_no": [1],
                        "channels": [
                            0,
                            1
                        ],
                        "location": {
                            "country": [
                                1
                            ],
                            "state": [
                                47
                            ]
                        }
                    }
                }
            ],
            "custom": "{\"Param\":\"\"}",
            "to": "2016-08-30T18:30:00",
            "user_id": "1205565",
            "type": 2
        }
        r = create_it_now(body=body)
        with open('/var/log/couponlogs/grocery/create_iocl.log', 'a+') as f:
            f.write(r.text)
            f.close()
