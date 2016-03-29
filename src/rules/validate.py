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
                        criteria.get('range_max') < criteria.get('range_min'):
            success = False
            error.append(u'range_max must not be less than range_min')

        if criteria.get('cart_range_max') and criteria.get('cart_range_min') and \
                        criteria.get('cart_range_max') < criteria.get('cart_range_min'):
            success = False
            error.append(u'cart_range_max must not be less than cart_range_min')

        in_categories = criteria.get('categories').get('in')

        not_in_categories = criteria.get('categories').get('not_in')

        if in_categories and not_in_categories:
            intersection = get_intersection_of_lists(in_categories, not_in_categories)
            if intersection:
                success = False
                error.append(
                    u'Categories[in] and Categories[not_in] must not have any category in common in a rule {}'.format(
                        intersection))

        in_products = criteria.get('products').get('in')

        not_in_products = criteria.get('products').get('not_in')

        if in_products and not_in_products:
            intersection = get_intersection_of_lists(in_products, not_in_products)
            if intersection:
                success = False
                error.append(
                    u'Products[in] and products[not_in] must not have any product in common in a rule {}'.format(
                        intersection))

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
        if not order.can_accommodate_new_vouchers:
            break

    if not order.existing_vouchers and len(args.get('coupon_codes', list())) > 0:
        return False, None, u'No matching items found for these coupons'
    else:
        return True, order, None
