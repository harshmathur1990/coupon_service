from src.enums import VoucherType
from dateutil import parser
from lib.utils import get_utc_timezone_unaware_date_object, is_valid_schedule_object, get_intersection_of_lists


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


def validate_for_create_api_v1(data):
    success = True
    error = list()

    voucher_type = data.get('type')

    rules = data.get('rules')

    success, error = validate_for_create_coupon(data)
    if not success:
        return success, error

    if voucher_type is VoucherType.regular_coupon.value:
        if len(rules) > 2 or len(rules) <= 0:
            success = False
            error.append(u'Minimum one rule and maximum two rules per voucher are supported')
            return success, error

        for rule in rules:
            benefits = rule.get('benefits')
            if benefits.get('freebies'):
                success = False
                error.append(u'Regular coupon should not have freebies')

        if len(rules) == 2:
            if not rules[0].get(
                    'criteria', dict()).get(
                'no_of_uses_allowed_per_user') == rules[1].get(
                'criteria', dict()).get('no_of_uses_allowed_per_user') or \
                    not rules[0].get('criteria', dict()).get(
                        'no_of_total_uses_allowed') == rules[1].get(
                        'criteria', dict()).get('no_of_total_uses_allowed'):
                success = False
                error.append(
                    u'Both the rules must same values for no_of_uses_allowed_per_user and no_of_total_uses_allowed')

    else:
        if len(rules) != 1:
            success = False
            error.append(u'Only one rule can be present in freebie vouchers')
            return success, error

        codes = data.get('code')

        if len(codes) != 1:
            success = False
            error.append(u'Only one voucher can be made of regular freebie and auto freebie type coupons')
            return success, error

        rule = rules[0]
        benefits = rule.get('benefits')
        criteria = rule.get('criteria')
        if not benefits.get('freebies') or benefits.get('amount') or benefits.get('percentage'):
            success = False
            error.append(u'Regular freebie and auto freebie must have freebie as benefit')

        if not criteria.get('location').get('zone') or len(criteria.get('location').get('zone')) != 1:
            success = False
            error.append(u'Only 1 zone can be present in regular or auto freebie coupon')

        if voucher_type is VoucherType.regular_freebie.value:
            # if criteria.get('cart_range_min') is None or criteria.get('cart_range_max') is None:
            #     success = False
            #     error.append(u'Cart Range min and Cart Range max is mandatory for regular freebie')
            pass

        else:

            if len(benefits.get('freebies')) != 1 or len(benefits.get('freebies')[0]) != 1:
                success = False
                error.append(u'Only 1 freebie is allowed per auto freebie voucher')

            # if criteria.get('range_min') is None or criteria.get('range_max') is None:
            #     success = False
            #     error.append(u'Range min and Range max is mandatory for auto freebie')

            if not criteria.get('variants') or len(criteria.get('variants')) != 1:
                success = False
                error.append(u'Only 1 variant is allowed in a auto freebie voucher')

    return success, error


def validate_for_update(data_list):
    if not isinstance(data_list, list):
        return False, u'Input is not list'

    for data in data_list:
        if not data.get('coupons') or not isinstance(data.get('coupons'), list):
            return False, u'Every element of input list must have a list of dicts with each dict containing from date and code'

        if not data.get('update') or not (
                            data.get('update').get('to')
                        # or data.get('update').get('schedule')
                    or data.get('update').get('description')
                or data.get('update').get('custom')):
            return False, u'At least one of [to, description, custom] must be present in update key'

        error = False
        for coupon_obj in data.get('coupons'):
            if isinstance(coupon_obj, dict):
                # error = u'coupons is not a list of dicts'

                if not coupon_obj.get('code'):
                    error = u'Voucher code missing'
                    break
                if coupon_obj.get('from'):
                    try:
                        from_date = parser.parse(coupon_obj.get('from'))
                        coupon_obj['from'] = get_utc_timezone_unaware_date_object(from_date)
                    except:
                        error = u'From Date is not valid'
                        break

        if error:
            return False, error

        if data.get('update').get('to'):
            try:
                to_date = parser.parse(data.get('update').get('to'))
                data['update']['to'] = get_utc_timezone_unaware_date_object(to_date)
            except ValueError:
                return False, u'Invalid Date format'

        # is_schedule_object_valid = is_valid_schedule_object(data.get('update'))
        # if not is_schedule_object_valid:
        #     return False, u'Schedule is not valid in update params'

        if data.get('update').get('schedule'):
            del data.get('update')['schedule']

    return True, None