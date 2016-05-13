import datetime
import logging

from src.enums import VoucherType
from utils import get_voucher

logger = logging.getLogger(__name__)


def validate_for_create_voucher(data_dict):
    error = list()
    success = True

    if not data_dict.get('force') and data_dict.get('from').date() < datetime.datetime.utcnow().date():
        success = False
        error.append(u'Backdated voucher creation is not allowed')

    if data_dict.get('to') < data_dict.get('from'):
        success = False
        error.append(u'Voucher end date must be greater than start date')

    return success, error


def validate_coupon(coupon_list, order, validate_for_apply=False):
    # returns failure only if we are unable to fetch details from
    # either of user, item or location APIs.
    # Otherwise it Will always return success regardless of coupon is valid/invalid
    # applicable etc.
    # If this method returns True, then order will be an Object of OrderData and
    # it will have failed_vouchers as a list and existing vouchers as list.

    for a_coupon in coupon_list:
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
    # if not order.existing_vouchers and len(args.get('coupon_codes', list())) > 0:
    #     # error_list.append(u'No matching items found for these coupons')
    #     return False, order, error_list
    # else:
    return error_list
