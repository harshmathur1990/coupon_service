from src.enums import *
from rule import Rule, RuleCriteria, Benefits
import uuid


def validate_for_create_coupon(data):
    error = list()
    success = True

    if data.get('use_type') in [UseType.global_use.value, UseType.both.value]\
            and not data.get('no_of_total_uses_allowed'):
        success = False
        error.append(u'no_of_total_uses_allowed is mandatory if use_type in (1,3')

    if data.get('use_type') in [UseType.per_user.value, UseType.both.value]\
            and not data.get('no_of_uses_allowed_per_user'):
        success = False
        error.append(u'no_of_uses_allowed_per_user is mandatory if use_type in (2,3')

    if data.get('range_min') and data.get('range_max') and data.get('range_max') < data.get('range_min'):
        success = False
        error.append(u'range_max must be greater than range_min')

    benefit_count = 0
    if data.get('freebies'):
        benefit_count += 1
    if data.get('amount'):
        benefit_count += 1
    if data.get('percentage'):
        benefit_count += 1

    if benefit_count > 1:
        success = False
        error.append(u'Benefit must have one of the values in freebies or amount or percentage')

    return success, error


def create_rule_object_and_persist(data):
    id = uuid.uuid1().hex
    rule_criteria_kwargs = dict()
    rule_criteria_keys = [
        'brands', 'categories', 'channels',
        'payment_modes', 'products', 'range_max',
        'range_min', 'sellers',  'storefronts',
        'use_type', 'no_of_uses_allowed_per_user',
        'no_of_total_uses_allowed', 'variants', 'location'
    ]
    location_keys = [
        'country', 'state', 'city', 'area', 'zone'
    ]
    for a_key in rule_criteria_keys:
        if a_key is not 'location':
            rule_criteria_kwargs[a_key] = data.get('key')
        else:
            location = data.get('location')
            for location_key in location_keys:
                rule_criteria_kwargs[location_key] = location.get(location_key)
    rule_criteria = RuleCriteria(**rule_criteria_kwargs)
    freebie_benefit_list = list()
    for freebie in data.get('freebies'):
        freebie_dict = dict()
        freebie_dict['type'] = BenefitType.freebie.value
        freebie_dict['value'] = freebie
        freebie_benefit_list.append(freebie_dict)
    amount_benefit = {
        'type': BenefitType.amount.value,
        'value': data.get('amount')
    }
    percentage_benefit = {
        'type': BenefitType.percentage.value,
        'value': data.get('percentage')
    }
    benefit_list = freebie_benefit_list
    benefit_list.append(amount_benefit)
    benefit_list.append(percentage_benefit)
    benefits = Benefits(max_discount=data.get('max_discount'), data=benefit_list)
    rule = Rule(id=id, name=data.get('name'), description=data.get('description'),
                criteria_json=rule_criteria.canonical_json(), benefits_json=benefits.canonical_json(),
                created_by=data.get('user_id'), updated_by=data.get('user_id'))
    result = rule.save()
    return result