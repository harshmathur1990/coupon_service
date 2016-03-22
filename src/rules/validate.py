import datetime
import logging
from data import OrderData
from utils import get_voucher, fetch_order_detail
from lib.utils import get_intersection_of_lists

logger = logging.getLogger(__name__)


def validate_for_create_coupon(data):
    error = list()
    success = True

    rules = data.get('rules')

    for rule in rules:
        criteria = rule.get('criteria')

        if criteria.get('range_max') and criteria.get('range_min') and \
                        criteria.get('range_max') <= criteria.get('range_min'):
            success = False
            error.append(u'range_max must be greater than range_min')

        if criteria.get('cart_range_max') and criteria.get('cart_range_min') and \
                        criteria.get('cart_range_max') <= criteria.get('cart_range_min'):
            success = False
            error.append(u'cart_range_max must be greater than cart_range_min')

        in_categories = criteria.get('categories').get('in')

        not_in_categories = criteria.get('categories').get('not_in')

        if in_categories and not_in_categories and get_intersection_of_lists(in_categories, not_in_categories):
            success = False
            error.append(u'Categories[in] and Categories[not_in] must not have any intersection in a rule')

    return success, error


def validate_for_create_voucher(data_dict):
    error = list()
    success = True

    if data_dict.get('from').date() < datetime.datetime.utcnow().date():
        success = False
        error.append(u'Backdated voucher creation is not allowed')

    if data_dict.get('to') < data_dict.get('from'):
        success = False
        error.append(u'Voucher end date must be greater than start date')

    return success, error


def validate_coupon(args):
    success, order, error = fetch_order_detail(args)
    assert isinstance(order, OrderData)
    if not success:
        return success, None, error

    for a_coupon in args.get('coupon_codes'):
        voucher = get_voucher(a_coupon)
        if not voucher:
            failed_dict = {
                'voucher': a_coupon,
                'error': u'Voucher does not exist'
            }
            order.failed_vouchers.append(failed_dict)
            continue
        voucher.match(order)
        if not order.can_accomodate_new_vouchers:
            break

    if order.existing_vouchers:
        return True, order, None
    else:
        return False, None, u'No matching items found for these coupons'
