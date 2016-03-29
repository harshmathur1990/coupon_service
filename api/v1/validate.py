from src.enums import VoucherType


def validate_for_create_api_v1(data):
    success = True
    error = list()

    voucher_type = data.get('type')

    rules = data.get('rules')

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

    else:
        if len(rules) != 1:
            success = False
            error.append(u'Only one rule can be present in freebie vouchers')
            return success, error

        codes = data.get('code')

        if len(codes) != 1:
            success = False
            error.append(u'Only one voucher can be made of regular and auto freebie type coupons')
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
            if criteria.get('cart_range_min') is None or criteria.get('cart_range_max') is None:
                success = False
                error.append(u'Cart Range min and Cart Range max is mandatory for regular freebie')

        else:

            if len(benefits.get('freebies')) != 1 or len(benefits.get('freebies')[0]) != 1:
                success = False
                error.append(u'Only 1 freebie is allowed per auto freebie voucher')

            if criteria.get('range_min') is None or criteria.get('range_max') is None:
                success = False
                error.append(u'Range min and Range max is mandatory for auto freebie')

            if not criteria.get('variants') or len(criteria.get('variants')) != 1:
                success = False
                error.append(u'Only 1 variant is allowed in a auto freebie voucher')

    return success, error
