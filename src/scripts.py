from src.sqlalchemydb import CouponsAlchemyDB
from lib.utils import make_api_call
from dateutil import parser
import binascii
import canonicaljson
import importlib
from src.rules.rule import Rule, Benefits
from config import method_dict
import hashlib


def do_it_now(body):
    headers = {
        'X-API-USER': 'admin',
        'X-API-TOKEN': 'kuchbhi'
    }
    r = make_api_call('http://api-service03.production.askme.com:9933/vouchers/v1/update', method='POST', headers=headers, body=body)
    return r


def do_iocl_date_correction():
    date_value = "2016-08-30 18:30:00.000000"
    date_value = parser.parse(date_value)
    db = CouponsAlchemyDB()
    get_voucher_query = 'select `code`, `from` from all_vouchers where `to` = :to'
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
        r = do_it_now(body=body)
        with open('/Users/harshmathur/Documents/update_to_date/output_iocl.log', 'a+') as f:
            f.write(r.text)
            f.close()



def do_date_correction():
    db = CouponsAlchemyDB()
    query = 'select count(1) c, `to` from all_vouchers group by `to` order by c desc'
    count_date_list = db.execute_raw_sql(query, dict())
    for count_date_map in count_date_list:
        date_value = count_date_map['to']
        count = count_date_map['c']
        get_voucher_query = 'select `code`, `from` from all_vouchers where `to` = :to'
        code_from_list = db.execute_raw_sql(get_voucher_query, {'to': date_value})
        code_from_list = [{'from': code_from_dict['from'].isoformat(), 'code': code_from_dict['code']} for code_from_dict in code_from_list]
        body = [
            {
                "coupons": code_from_list,
                "update": {
                    "to": date_value.isoformat()
                }
            }
        ]
        r = do_it_now(body=body)
        with open('/Users/harshmathur/Documents/update_to_date/output.log', 'a+') as f:
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