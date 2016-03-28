import binascii
from src.sqlalchemydb import CouponsAlchemyDB
from src.enums import RuleType
from src.rules.vouchers import Vouchers
from src.rules.utils import create_rule_object, save_vouchers


def create_freebie_coupon(args):
    # code must have only 1 element and it has been validated before
    # hence safe in accessing directly 0th element
    # in case of update, delete the voucher, delete entry from auto_freebie_search
    # create a new rule and create a new voucher on the created rule, and an entry in auto_freebie_search
    # Also it is ensured that at a time only one entry per zone, spending range and category can be there.
    code = args.get('code')[0]
    rule = args.get('rules')[0]
    criteria = rule.get('criteria')
    if args.get('type') is RuleType.auto_freebie.value:
        db = CouponsAlchemyDB()
        existing_voucher = db.find("auto_freebie_search", **{
            'type': RuleType.auto_freebie.value,
            'category': criteria.get('categories').get('in')[0],
            'zone': criteria.get('location').get('zone')[0],
            'range_min': criteria.get('range_min'),
            'range_max': criteria.get('range_max')
        })
        if existing_voucher:
            voucher = Vouchers.find_one_by_id(existing_voucher[0]['voucher_id'])
            if voucher.code != code:
                return False, None, u'Existing voucher exists for the given criteria with code {}'.format(voucher.code)
            db.delete_row("auto_freebie_search", **{'voucher_id': binascii.a2b_hex(voucher.id)})
            db.delete_row("vouchers", **{'id': binascii.a2b_hex(voucher.id)})

        data = {
            'criteria': {
                'categories': {
                    'in': criteria.get('categories').get('in'),
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
                'cart_range_min': None,
                'cart_range_max': None,
                'channels': [],
                'brands': [],
                'products': [],
                'storefronts': [],
                'variants': [],
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
        rule_obj = create_rule_object(data, RuleType.auto_freebie.value, args.get('user_id'))
        rule_obj.save()
        success_list, error_list = save_vouchers(args, [rule_obj.id])
        if not error_list:
            voucher_id = success_list[0]['id']
            auto_freebie_values = dict()
            auto_freebie_values['type'] = RuleType.auto_freebie.value
            auto_freebie_values['zone'] = criteria.get('location').get('zone')[0],
            auto_freebie_values['range_min'] = criteria.get('range_min')
            auto_freebie_values['range_max'] = criteria.get('range_max')
            auto_freebie_values['voucher_id'] = binascii.a2b_hex(voucher_id)
            auto_freebie_values['category'] = criteria.get('categories').get('in')[0]
            db.insert_row("auto_freebie_search", **auto_freebie_values)
    else:
        db = CouponsAlchemyDB()
        existing_voucher = db.find("auto_freebie_search", **{
            'type': RuleType.regular_freebie.value,
            'category': None,
            'zone': criteria.get('location').get('zone')[0],
            'cart_range_min': criteria.get('cart_range_min'),
            'cart_range_max': criteria.get('cart_range_max'),
        })
        if existing_voucher:
            voucher = Vouchers.find_one_by_id(existing_voucher[0]['voucher_id'])
            if voucher.code != code:
                return False, None, u'Existing voucher exists for the given criteria with code {}'.format(voucher.code)
            db.delete_row("auto_freebie_search", **{'voucher_id': binascii.a2b_hex(voucher.id)})
            db.delete_row("vouchers", **{'id': binascii.a2b_hex(voucher.id)})
        data = {
            'criteria': {
                'categories': {
                    'in': [],
                    'not_in': []
                },
                'location': {
                    'country': [],
                    'state': [],
                    'area': [],
                    'city': [],
                    'zone': criteria.get('location').get('zone')
                },
                'no_of_uses_allowed_per_user': criteria.get('no_of_uses_allowed_per_user'),
                'no_of_total_uses_allowed': criteria.get('no_of_total_uses_allowed'),
                'valid_on_order_no': criteria.get('valid_on_order_no'),
                'cart_range_min': criteria.get('cart_range_min'),
                'cart_range_max': criteria.get('cart_range_max'),
                'range_min': None,
                'range_max': None,
                'channels': [],
                'brands': [],
                'products': [],
                'storefronts': [],
                'variants': [],
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
        rule_obj = create_rule_object(data, RuleType.regular_freebie.value, args.get('user_id'))
        rule_obj.save()
        success_list, error_list = save_vouchers(args, [rule_obj.id])
        if not error_list:
            voucher_id = success_list[0]['id']
            auto_freebie_values = dict()
            auto_freebie_values['type'] = RuleType.regular_freebie.value
            auto_freebie_values['zone'] = criteria.get('location').get('zone')[0],
            auto_freebie_values['cart_range_min'] = criteria.get('cart_range_min')
            auto_freebie_values['cart_range_max'] = criteria.get('cart_range_max')
            auto_freebie_values['voucher_id'] = binascii.a2b_hex(voucher_id)
            db.insert_row("auto_freebie_search", **auto_freebie_values)
    return True, success_list, error_list
