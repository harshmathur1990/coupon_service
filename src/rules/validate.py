import datetime
import logging
from data import OrderData
from utils import get_voucher, fetch_order_detail
from lib.utils import get_intersection_of_lists
from src.enums import VoucherType

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


def validate_coupon(args, validate_for_apply=False):
    success, order, error = fetch_order_detail(args)
    if not success:
        return success, None, [error]
    assert isinstance(order, OrderData)

    for a_coupon in args.get('coupon_codes', list()):
        voucher, error = get_voucher(a_coupon)
        if not voucher:
            failed_dict = {
                'voucher': a_coupon,
                'error': error
            }
            order.failed_vouchers.append(failed_dict)
            continue
        if validate_for_apply:
            voucher.match(order)
        else:
            if voucher.type is VoucherType.regular_coupon.value:
                voucher.match(order)

        # if not order.can_accommodate_new_vouchers:
        #     break

    error_list = [failed_vouchers['error'] for failed_vouchers in order.failed_vouchers]
    if not order.existing_vouchers and len(args.get('coupon_codes', list())) > 0:
        # error_list.append(u'No matching items found for these coupons')
        return False, order, error_list
    else:
        return True, order, error_list
