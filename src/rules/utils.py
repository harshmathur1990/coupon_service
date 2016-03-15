import datetime
from vouchers import Vouchers, VoucherTransactionLog
from src.enums import BenefitType, Channels
from lib import cache
from rule import Rule
import uuid
from constants import RULE_CACHE_KEY


def get_rule(rule_id):
    rule = Rule.find_one(rule_id)
    if rule:
        return rule
    return None


def get_voucher(voucher_code):
    voucher = Vouchers.find_one(voucher_code)
    if voucher and voucher.to_date > datetime.datetime.utcnow():
        return voucher
    return None


def get_intersection_of_lists(list1, list2, key=None):
    if not key:
        return [l for l in list1 if l in list2]
    else:
        return [l[key] for l in list1 if l in list2]


def get_benefits(data, coupon_code):
    '''

    :param data: {'rule': Rule, 'items': list of VerificationItemData, 'total': 1000}
    :return:
    '''
    benefit_dict = dict()
    rule = data['rule']
    assert isinstance(rule, Rule), u'rule is not of Type Rule'
    benefits = rule.benefits_obj
    max_discount = benefits.maximum_discount
    benefit_list = benefits.data
    freebie_list = list()
    products_list = list()
    discount = 0.0
    for benefit in benefit_list:
        benefit_type = BenefitType(benefit['type'])
        if benefit_type is BenefitType.freebie:
            freebie_list.append(benefit)
        if benefit_type is BenefitType.amount:
            discount = benefit['value']
            if discount > max_discount:
                discount = max_discount
            for item in data['items']:
                product_dict = dict()
                product_dict['item_id'] = item.variant
                product_dict['qty'] = item.quantity
                product_dict['discount'] = (item.quantity * item.price * discount)/data.get('total')
                products_list.append(product_dict)
        if benefit_type is BenefitType.percentage:
            discount = benefit['value'] * data.get('total') / 100
            if discount > max_discount:
                discount = max_discount
            for item in data['items']:
                product_dict = dict()
                product_dict['subscriptionId'] = item.variant
                product_dict['qty'] = item.quantity
                product_dict['discount'] = (item.quantity * item.price * discount)/data.get('total')
                products_list.append(product_dict)
    benefit_dict['products'] = products_list
    benefit_dict['freebies'] = freebie_list
    benefit_dict['totalDiscount'] = discount
    benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
    benefit_dict['channel'] = [Channels(c).name for c in rule.criteria_obj.channels]
    benefit_dict['couponCodes'] = [coupon_code]
    benefit_dict['status'] = 'success'
    return benefit


def apply_benefits(args, benefit):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    voucher_code = args.get('coupon_codes')[0]
    voucher_id = get_voucher(voucher_code).id
    transaction_log = VoucherTransactionLog(**{
        'id': uuid.uuid1().hex,
        'user_id': user_id,
        'voucher_id': voucher_id,
        'order_id': order_id
    })
    return transaction_log.save()
