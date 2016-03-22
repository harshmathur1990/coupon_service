from src.enums import RuleType


def validate_for_create_api_v1(data):
    success = True
    error = list()

    voucher_type = data.get('type')

    rules = data.get('rules')

    if voucher_type is RuleType.regular_coupon.value:
        if len(rules) > 2 or len(rules) <= 0:
            success = False
            error.append(u'Minimum 1 rule and maximum 2 rules per voucher are supported')
            return success, error

        for rule in rules:
            benefits = rule.get('benefits')
            if benefits.get('freebies'):
                success = False
                error.append(u'Regular coupon should not have freebies')

    else:
        if len(rules) != 1:
            success = False
            error.append(u'Only 1 rule can be present in freebie vouchers')
            return success, error

        for rule in rules:
            benefits = rule.get('benefits')

            if not benefits.get('freebies') or benefits.get('amount') or benefits.get('percentage'):
                success = False
                error.append(u'Regular freebie and auto freebie must have freebie as benefit')

    return success, error
