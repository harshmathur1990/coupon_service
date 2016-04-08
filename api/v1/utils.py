import binascii
from src.sqlalchemydb import CouponsAlchemyDB
from src.enums import VoucherType
from src.rules.utils import find_overlapping_vouchers
from src.rules.utils import create_rule_object, save_vouchers, save_auto_freebie_from_voucher_dict


def create_freebie_coupon(args):
    # code must have only 1 element and it has been validated before
    # hence safe in accessing directly 0th element
    # in case of update, delete the voucher, delete entry from auto_freebie_search
    # create a new rule and create a new voucher on the created rule, and an entry in auto_freebie_search
    # Also it is ensured that at a time only one entry per zone, spending range and category can be there.
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

    success, error_list = find_overlapping_vouchers(existing_voucher_dict)
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