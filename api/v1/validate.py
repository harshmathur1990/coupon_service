from src.enums import RuleType


def validate_for_create_api_v1(data):
    success = True
    error = list()

    voucher_type = data.get('type')

    rules = data.get('rules')

    if voucher_type is RuleType.regular_coupon.value:
        if len(rules) > 2 or len(rules) <= 0:
            success = False
            error.append(u'Only 2 rules per voucher is supported in this version')
            return success, error

    else:
        if len(rules) != 1:
            success = False
            error.append(u'Only 1 rule can be present in freebie vouchers')

    benefits = data.get('benefits')
    benefit_count = 0

    if benefits.get('freebies'):
        benefit_count += 1
    if benefits.get('amount'):
        benefit_count += 1
    if benefits.get('percentage'):
        benefit_count += 1

    if benefit_count != 1:
        success = False
        error.append(u'One rule can have only one of freebies, amount or percentage')
    return success, error
