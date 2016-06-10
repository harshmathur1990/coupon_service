from src.sqlalchemydb import CouponsAlchemyDB
from lib.utils import make_api_call
from dateutil import parser

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
