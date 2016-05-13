import datetime
import json
import logging
import uuid
from datetime import timedelta

import croniter
from dateutil import parser

from api.v1.data import OrderData
from lib.utils import get_intersection_of_lists, is_between, get_num_from_str
from rule import Rule
from src.enums import *
from src.sqlalchemydb import CouponsAlchemyDB
from vouchers import Vouchers, VoucherTransactionLog

logger = logging.getLogger(__name__)


def get_voucher(voucher_code):
    voucher = Vouchers.find_one(voucher_code)
    now = datetime.datetime.utcnow()
    if voucher and voucher.from_date <= now <= voucher.to_date:
        if voucher.schedule:
            for schedule in voucher.schedule:
                if schedule['type'] is SchedulerType.exact.value:
                    scheduled_time_start = parser.parse(schedule['value'])
                    weeks, days, hours, minutes, seconds = tuple(schedule['duration'].split(':'))
                    scheduled_time_end = scheduled_time_start + timedelta(days=get_num_from_str(days), weeks=get_num_from_str(weeks), hours=get_num_from_str(hours), minutes=get_num_from_str(minutes), seconds=get_num_from_str(seconds))
                    if is_between(now, scheduled_time_start, scheduled_time_end):
                        return voucher, None
                elif schedule['type'] is SchedulerType.daily.value:
                    today_time = parser.parse(schedule['value'])
                    now = datetime.datetime.utcnow()
                    weeks, days, hours, minutes, seconds = tuple(schedule['duration'].split(':'))
                    scheduled_time_start_curr = now.replace(hour=today_time.hour, minute=today_time.minute, second=today_time.second)
                    scheduled_time_end_curr = scheduled_time_start_curr + timedelta(days=get_num_from_str(days), weeks=get_num_from_str(weeks), hours=get_num_from_str(hours), minutes=get_num_from_str(minutes), seconds=get_num_from_str(seconds))
                    scheduled_time_start_prev = scheduled_time_start_curr - timedelta(days=1)
                    scheduled_time_end_prev = scheduled_time_end_curr - timedelta(days=1)
                    if is_between(now, scheduled_time_start_curr, scheduled_time_end_curr) or is_between(now, scheduled_time_start_prev, scheduled_time_end_prev):
                        return voucher, None
                elif schedule['type'] is SchedulerType.cron.value:
                    cron = croniter.croniter(schedule['value'], now)
                    cron_prev = cron.get_prev(datetime.datetime)
                    cron_current = cron.get_current(datetime.datetime)
                    cron_next = cron.get_next(datetime.datetime)
                    weeks, days, hours, minutes, seconds = tuple(schedule['duration'].split(':'))
                    deltatime = timedelta(days=get_num_from_str(days), weeks=get_num_from_str(weeks),
                                          hours=get_num_from_str(hours), minutes=get_num_from_str(minutes),
                                          seconds=get_num_from_str(seconds))
                    duration_prev = cron_prev + deltatime
                    duration_current = cron_current + deltatime
                    duration_next = cron_next + deltatime
                    if is_between(now, cron_prev, duration_prev) or \
                            is_between(now, cron_current, duration_current) or \
                            is_between(now, cron_next, duration_next):
                        return voucher, None
            return None, u'The voucher {} is not valid'.format(voucher.code)
        return voucher, None
    elif voucher and now > voucher.to_date:
        active_voucher = Vouchers.fetch_active_voucher(voucher_code)
        if active_voucher:
            return get_voucher(voucher_code)

    return None, u'The voucher {} does not exist'.format(voucher_code)


def get_benefits_new(order):
    assert isinstance(order, OrderData)
    products_dict = dict()
    benefits_list = list()
    payment_modes_list = list()
    channels_list = list()
    for item in order.items:
        product_dict = dict()
        product_dict['itemid'] = item.subscription_id
        product_dict['quantity'] = item.quantity
        product_dict['discount'] = 0.0
        products_dict[item.subscription_id] = product_dict
    for existing_voucher in order.existing_vouchers:
        rules = existing_voucher['voucher'].rules_list
        for rule in rules:
            benefits = rule.benefits_obj
            benefit_list = benefits.data
            total = existing_voucher['total']
            subscription_id_list = existing_voucher['subscription_id_list']
            max_discount = benefits.max_discount
            benefit_dict = dict()
            for benefit in benefit_list:
                if benefit['value'] is 0 and benefit['type'] == BenefitType.amount.value and existing_voucher['voucher'].custom:
                    pass
                elif not benefit['value']:
                    continue
                flat_discount = 0.0
                percentage_discount = 0.0
                percentage_discount_actual = 0.0
                freebie_list = list()
                benefit_type = BenefitType(benefit['type'])
                if benefit_type is BenefitType.freebie:
                    freebie_list.append(benefit['value'])
                else:
                    if benefit_type is BenefitType.amount and benefit['value']:
                        flat_discount = benefit['value']
                    elif benefit_type is BenefitType.percentage and benefit['value']:
                        percentage = benefit['value']
                        percentage_discount = percentage * total / 100
                        percentage_discount_actual = percentage_discount
                    if max_discount and flat_discount > max_discount:
                        flat_discount = max_discount
                    if max_discount and percentage_discount > max_discount:
                        percentage_discount = max_discount
                    for item in order.items:
                        if item.subscription_id in subscription_id_list:
                            if flat_discount:
                                item_flat_discount = (item.quantity * item.price * flat_discount)/total
                                products_dict[item.subscription_id]['discount'] = max(
                                    products_dict[item.subscription_id]['discount'], item_flat_discount)
                            if percentage_discount:
                                item_percentage_discount = (item.quantity * item.price * percentage_discount)/total
                                products_dict[item.subscription_id]['discount'] = max(
                                    products_dict[item.subscription_id]['discount'], item_percentage_discount)
                benefit_dict['couponCode'] = existing_voucher['voucher'].code
                benefit_dict['flat_discount'] = flat_discount
                benefit_dict['prorated_discount'] = percentage_discount
                benefit_dict['prorated_discount_actual'] = percentage_discount_actual
                benefit_dict['freebies'] = freebie_list
                benefit_dict['items'] = subscription_id_list
                benefit_dict['type'] = existing_voucher['voucher'].type
                benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
                benefit_dict['channel'] = [Channels(c).value for c in rule.criteria_obj.channels]
                benefit_dict['custom'] = existing_voucher['voucher'].custom
                if max_discount:
                    benefit_dict['max_discount'] = max_discount
                else:
                    benefit_dict['max_discount'] = None
                benefits_list.append(benefit_dict)
                if not payment_modes_list:
                    payment_modes_list = benefit_dict['paymentMode']
                else:
                    payment_modes_list = get_intersection_of_lists(payment_modes_list, benefit_dict['paymentMode'])
                if not channels_list:
                    channels_list = benefit_dict['channel']
                else:
                    channels_list = get_intersection_of_lists(channels_list, benefit_dict['channel'])
    total_discount = 0.0
    products_list = list()
    for item in products_dict:
        product_dict = products_dict[item]
        products_list.append(product_dict)
        total_discount += product_dict['discount']
        product_dict['discount'] = round(product_dict['discount'], 2)

    for a_benefit in benefits_list:
        # if a_benefit.get('prorated_discount_actual'):
        a_benefit['prorated_discount'] = a_benefit['prorated_discount_actual']
        del a_benefit['prorated_discount_actual']

    total_discount = round(total_discount, 2)
    response_dict = dict()

    response_dict['products'] = products_list
    response_dict['benefits'] = benefits_list
    response_dict['totalDiscount'] = total_discount
    response_dict['paymentMode'] = payment_modes_list
    response_dict['channel'] = channels_list
    response_dict['couponCodes'] = [existing_voucher['voucher'].code for existing_voucher in order.existing_vouchers]
    return response_dict


def apply_benefits(args, order, benefits):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    voucher_id_list = list()
    db = CouponsAlchemyDB()
    db.begin()
    try:
        for existing_voucher in order.existing_vouchers:
            voucher_id = existing_voucher['voucher'].id
            if voucher_id in voucher_id_list:
                continue
            voucher_id_list.append(voucher_id)
            rule = existing_voucher['voucher'].rules_list[0]
            status = rule.criteria_obj.check_usage(order.customer_id, existing_voucher['voucher'].id_bin, db)
            if not status.get('success', False):
                db.rollback()
                return False, 400, u'Voucher {} has expired'.format(existing_voucher['voucher'].code)
            transaction_log = VoucherTransactionLog(**{
                'id': uuid.uuid1().hex,
                'user_id': user_id,
                'voucher_id': voucher_id,
                'order_id': order_id,
                'status': VoucherTransactionStatus.in_progress.value,
                'response': json.dumps(benefits)
            })
            transaction_log.save(db)
        db.commit()
    except Exception as e:
        logger.exception(e)
        db.rollback()
        return False, 500, u'Unknown Error. Please try after some time'
    # else:
    #     db.commit()
    return True, 200, None


def save_rule_list(rule_list):
    rule_id_list = list()
    for rule in rule_list:
        rule.save()
        rule_id_list.append(rule.id)
    return rule_id_list


def create_voucher_object(data, rule_id_list, code):
    kwargs = dict()
    id = uuid.uuid1().hex
    kwargs['id'] = id
    kwargs['created_by'] = data.get('user_id')
    kwargs['code'] = code
    kwargs['rules'] = ','.join(rule_id_list)
    kwargs['description'] = data.get('description')
    kwargs['from'] = data.get('from')
    kwargs['to'] = data.get('to')
    kwargs['type'] = data.get('type')
    kwargs['schedule'] = data.get('schedule')
    kwargs['updated_by'] = data.get('user_id')
    kwargs['custom'] = data.get('custom')
    voucher = Vouchers(**kwargs)
    return voucher


def save_vouchers(args, rule_id_list):
    success_list = list()
    error_list = list()
    code_list = set(args.get('code'))
    for code in code_list:
        voucher = create_voucher_object(args, rule_id_list, code)
        success, data, error = voucher.save()
        if not success:
            error = {
                'code': code,
                'error': error,
                'reason': error
            }
            error_list.append(error)
        else:
            success_list.append(data)
    return success_list, error_list


def create_rule_object(data, user_id=None):
    description = data.get('description')
    from api.v1.utils import get_criteria_kwargs
    rule_criteria, rule_blacklist_criteria, benefits = get_criteria_kwargs(data)
    id = uuid.uuid1().hex
    rule = Rule(id=id, description=description, blacklist_criteria_json=rule_blacklist_criteria.canonical_json(),
                criteria_json=rule_criteria.canonical_json(), benefits_json=benefits.canonical_json(),
                created_by=user_id, updated_by=user_id, criteria_obj=rule_criteria, benefits_obj=benefits)
    return rule


def create_rule_list(args):
    rule_list = list()
    for rule in args.get('rules', list()):
        rule_list.append(create_rule_object(rule, args.get('user_id')))
    return rule_list


def create_and_save_rule_list(args):
    rule_list = create_rule_list(args)
    return save_rule_list(rule_list), rule_list


def fetch_order_response(args):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    db = CouponsAlchemyDB()
    result = db.find("voucher_use_tracker", **{'order_id': order_id, 'user_id': user_id})
    if result:
        # result may have one entry per voucher,
        # but all entries will have same json for an order id,
        # Hence its safe accessing the list's 0th element
        return True, json.loads(result[0]['response'])
    return False, None


def fetch_voucher_for_coupon_details(coupon, db):
    from_date = None
    if isinstance(coupon, dict):
        from_date = coupon.get('from')
        code = coupon.get('code')
    else:
        code = coupon
    if from_date:
        voucher = Vouchers.find_one_all_vouchers(code, from_date, db)
        if not voucher:
            return False, None, u'Voucher code {} with from date as {} not found'.format(code, from_date.isoformat())
    else:
        # from date not given, check if only one voucher exist,
        # then update to date, else return with error
        voucher_list = Vouchers.find_all_by_code(code, db)
        if not voucher_list:
            return False, None, u'Voucher code {} not found'.format(code)
        if len(voucher_list) != 1:
            return False, None, u'Multiple Vouchers found with code {}, Please provide from date'.format(code)
        voucher = voucher_list[0]
    return True, voucher, None


def update_coupon(coupon, update_dict):
    db = CouponsAlchemyDB()
    db.begin()
    try:
        success, voucher, error = fetch_voucher_for_coupon_details(coupon, db)
        if not success:
            db.rollback()
            return False, error
        success, error_list = voucher.update(update_dict, db)
        if not success:
            db.rollback()
            return False, u','.join(error_list)
        db.commit()
    except Exception as e:
        logger.exception(e)
        db.rollback()
        return False, u'Unknown Error. Please Contact tech support'
    return True, None


def update_values_in_this_list_of_coupons(data):
    success_list = list()
    error_list = list()
    coupon_list = data.get('coupons')
    to_date = data['update'].get('to')
    schedule = data['update'].get('schedule')
    custom = data['update'].get('custom')
    description = data['update'].get('description')
    update_dict = dict()
    if schedule:
        update_dict['schedule'] = schedule
    if custom:
        update_dict['custom'] = custom
    if description:
        update_dict['description'] = description
    if to_date:
        update_dict['to'] = to_date
    for coupon in coupon_list:
        if isinstance(coupon, dict):
            code = coupon.get('code')
        else:
            code = coupon
        success, error = update_coupon(coupon, update_dict)
        if not success:
            error_dict = {
                'code': code,
                'error': error
            }
            error_list.append(error_dict)
            continue
        success_dict = {
            'code': code
        }
        success_list.append(success_dict)
    return success_list, error_list


def update_keys_in_input_list(data_list):
    success_list = list()
    error_list = list()
    for data in data_list:
        success_list_in_this_data, error_list_in_this_data = update_values_in_this_list_of_coupons(data)
        success_list += success_list_in_this_data
        error_list += error_list_in_this_data
    return success_list, error_list


def is_validity_period_exclusive_for_voucher_code(voucher, db=None):
    if not db:
        db = CouponsAlchemyDB()
    date_overlapping_caluse = '(((:from >= `from` && :from <= `to`) or (:to >= `from` && :to <= `to`)) or ((`from` >= :from && `from` <= :to) or (`to` >= :from && `to` <= :to) ))'
    date_overlap_params = {
        'from': voucher.from_date,
        'to': voucher.to_date,
        'code': voucher.code
    }
    sql = "select * from all_vouchers where code=:code && ("+date_overlapping_caluse+")"
    voucher_list = db.execute_raw_sql(sql, date_overlap_params)
    if voucher_list:
        return False, u'Vouchers with overlapping dates found for code {}'.format(voucher.code)
    return True, None


def is_auto_benefit_voucher(type):
    if type is VoucherType.auto_freebie.value or type is VoucherType.regular_freebie.value:
        return True
    return False
