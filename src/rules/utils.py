import datetime
import json
import logging
import uuid
from datetime import timedelta

import croniter
from dateutil import parser

from lib.utils import is_between, get_num_from_str, create_error_response,\
    get_intersection_of_lists, get_utc_timezone_unaware_date_object, create_success_response
from rule import Rule
from src.enums import *
from src.enums import BenefitType, Channels
from src.sqlalchemydb import CouponsAlchemyDB
from vouchers import Vouchers, VoucherTransactionLog
from . import default_error_message
logger = logging.getLogger(__name__)


def get_voucher(voucher_code, order_date=None):
    if order_date:
        voucher = Vouchers.find_voucher_at_the_date(voucher_code, order_date)
        if not voucher:
            return None, default_error_message
        return voucher, None
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
            return None, default_error_message
        return voucher, None
    elif voucher and now > voucher.to_date:
        active_voucher = Vouchers.fetch_active_voucher(voucher_code)
        if active_voucher:
            return get_voucher(voucher_code)

    return None, default_error_message


def apply_benefits(args, order, benefits):
    order_id = args.get('order_id')
    user_id = args.get('customer_id')
    voucher_id_list = list()
    db = CouponsAlchemyDB()
    db.begin()
    try:
        rows_with_order_id = db.find("voucher_use_tracker", **{'order_id': order_id})
        if rows_with_order_id:
            db.delete_row_in_transaction("voucher_use_tracker", **{'order_id': order_id})
        for existing_voucher in order.existing_vouchers:
            voucher_id = existing_voucher['voucher'].id
            if voucher_id in voucher_id_list:
                continue
            voucher_id_list.append(voucher_id)
            rule = existing_voucher['voucher'].rules_list[0]
            if hasattr(order, 'validate') and not order.validate:
                pass
            else:
                success, error = rule.criteria_obj.check_usage(order.customer_id, existing_voucher['voucher'].id_bin, order_id, db)
                if not success:
                    db.rollback()
                    return False, 400, default_error_message

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


def create_rule_object(data, user_id=None, get_criteria_kwargs=None):
    description = data.get('description')
    rule_criteria, rule_blacklist_criteria, benefits = get_criteria_kwargs(data)
    id = uuid.uuid1().hex
    rule = Rule(id=id, description=description, blacklist_criteria_json=rule_blacklist_criteria.canonical_json(),
                criteria_json=rule_criteria.canonical_json(), benefits_json=benefits.canonical_json(),
                created_by=user_id, updated_by=user_id, criteria_obj=rule_criteria, benefits_obj=benefits)
    return rule


def create_rule_list(args, get_criteria_kwargs):
    rule_list = list()
    for rule in args.get('rules', list()):
        rule_list.append(create_rule_object(rule, args.get('user_id'), get_criteria_kwargs))
    return rule_list


def create_and_save_rule_list(args, get_criteria_kwargs):
    rule_list = create_rule_list(args, get_criteria_kwargs)
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


def update_coupon(coupon, update_dict, change_id):
    db = CouponsAlchemyDB()
    db.begin()
    try:
        success, voucher, error = fetch_voucher_for_coupon_details(coupon, db)
        if not success:
            db.rollback()
            return False, error
        success, error_list = voucher.update(update_dict, db, change_id)
        if not success:
            db.rollback()
            return False, u','.join(error_list)
        db.commit()
    except Exception as e:
        logger.exception(e)
        db.rollback()
        return False, u'Unknown Error. Please Contact tech support'
    return True, None


def update_values_in_this_list_of_coupons(data, change_id):
    success_list = list()
    error_list = list()
    coupon_list = data.get('coupons')
    to_date = data['update'].get('to')
    schedule = data['update'].get('schedule')
    custom = data['update'].get('custom')
    description = data['update'].get('description')
    is_active = 'is_active' in data['update']
    update_dict = dict()
    if schedule:
        update_dict['schedule'] = schedule
    if custom:
        update_dict['custom'] = custom
    if description:
        update_dict['description'] = description
    if to_date:
        update_dict['to'] = to_date
    if is_active:
        update_dict['is_active'] = data['update'].get('is_active')
    update_dict['force'] = data.get('force', False)
    for coupon in coupon_list:
        if isinstance(coupon, dict):
            code = coupon.get('code')
        else:
            code = coupon
        success, error = update_coupon(coupon, update_dict, change_id)
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
    db = CouponsAlchemyDB()
    db.begin()
    change_id = None
    try:
        db.insert_row("all_vouchers_log_sequence")
        query = 'select last_insert_id() as id'
        max_change_log = db.execute_raw_sql(query, dict())
        change_id = max_change_log[0]['id']
        db.commit()
    except Exception as e:
        logger.exception(e)
        db.rollback()
        change_id = None
    success_list = list()
    error_list = list()
    if change_id:
        for data in data_list:
            success_list_in_this_data, error_list_in_this_data = update_values_in_this_list_of_coupons(data, change_id=change_id)
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


def make_transaction_log_entry(args):
    success, error = VoucherTransactionLog.make_transaction_log_entry(args)
    if not success:
        rv = create_error_response(400, error)
    else:
        rv = {'success': success}
    return rv


def get_benefits_new(order):
    products_dict = dict()
    benefits_list = list()
    payment_modes_list = list()
    channels_list = list()
    for item in order.items:
        product_dict = dict()
        product_dict['itemid'] = item.item_id
        product_dict['quantity'] = item.quantity
        product_dict['discount'] = 0.0
        product_dict['agent_discount'] = 0.0
        product_dict['cashback'] = 0.0
        product_dict['agent_cashback'] = 0.0
        products_dict[item.item_id] = product_dict
    for existing_voucher in order.existing_vouchers:
        rules = existing_voucher['voucher'].rules_list
        for rule in rules:
            benefits = rule.benefits_obj
            benefit_list = benefits.data
            total = existing_voucher['total']
            item_id_list = existing_voucher['item_id_list']
            custom_dict = None
            if not benefit_list and existing_voucher['voucher'].custom:
                try:
                    custom_dict = json.loads(existing_voucher['voucher'].custom)
                except:
                    pass
                if custom_dict and custom_dict.get('Param'):
                    cashback = {
                        'type': BenefitType.cashback_amount.value,
                        'value': '?'
                    }
                    benefit_list.append(cashback)
            for benefit in benefit_list:
                benefit_dict = dict()
                benefit_dict['max_cap'] = None
                amount = 0.0
                amount_actual = 0.0
                max_cap = 0.0
                freebie_list = list()
                benefit_type = BenefitType(benefit['type'])
                if benefit_type is BenefitType.freebie:
                    freebie_list.append(benefit['value'])
                else:
                    if benefit['value'] is None:
                        continue
                    if benefit_type in [
                        BenefitType.amount,
                        BenefitType.cashback_amount,
                        BenefitType.agent_amount,
                        BenefitType.agent_cashback_amount,
                    ]:
                        amount = benefit['value']

                    elif benefit_type in [
                        BenefitType.percentage,
                        BenefitType.cashback_percentage,
                        BenefitType.agent_percentage,
                        BenefitType.agent_cashback_percentage
                    ]:
                        percentage = benefit['value']
                        amount = percentage * total / 100
                        amount_actual = amount
                        max_cap = benefit.get('max_cap')
                        benefit_dict['max_cap'] = max_cap
                        if max_cap and amount > max_cap:
                            amount = max_cap

                    if benefit_type is BenefitType.cashback_amount and benefit['value']:
                        amount = 0 if benefit['value'] == '?' else benefit['value']

                    for item in order.items:

                        if item.item_id in item_id_list:

                            item_amount = (item.quantity * item.price * amount)/total

                            if benefit_type in [
                                BenefitType.amount,
                                BenefitType.percentage
                            ]:
                                products_dict[item.item_id]['discount'] = max(
                                    products_dict[item.item_id]['discount'], item_amount)

                            if benefit_type in [
                                BenefitType.cashback_amount,
                                BenefitType.cashback_percentage
                            ]:
                                products_dict[item.item_id]['cashback'] = max(
                                    products_dict[item.item_id]['cashback'], item_amount)

                            if benefit_type in [
                                BenefitType.agent_amount,
                                BenefitType.agent_percentage
                            ]:
                                products_dict[item.item_id]['agent_discount'] = max(
                                    products_dict[item.item_id]['agent_discount'], item_amount)

                            if benefit_type in [
                                BenefitType.agent_cashback_amount,
                                BenefitType.agent_cashback_percentage
                            ]:
                                products_dict[item.item_id]['agent_cashback'] = max(
                                    products_dict[item.item_id]['agent_cashback'], item_amount)

                benefit_dict['couponCode'] = existing_voucher['voucher'].code
                benefit_dict['benefit_type'] = benefit_type.value
                if existing_voucher['voucher'].type in [VoucherType.auto_freebie.value, VoucherType.regular_freebie.value]:
                    benefit_dict['freebies'] = freebie_list
                else:
                    benefit_dict['amount'] = amount
                    benefit_dict['amount_actual'] = amount_actual
                benefit_dict['items'] = item_id_list
                benefit_dict['type'] = existing_voucher['voucher'].type
                benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
                benefit_dict['channel'] = [Channels(c).value for c in rule.criteria_obj.channels]
                benefit_dict['custom'] = existing_voucher['voucher'].custom

                benefits_list.append(benefit_dict)

                if not payment_modes_list:
                    payment_modes_list = benefit_dict['paymentMode']
                else:
                    payment_modes_list = get_intersection_of_lists(payment_modes_list, benefit_dict['paymentMode'])

                if not channels_list:
                    channels_list = benefit_dict['channel']
                else:
                    channels_list = get_intersection_of_lists(channels_list, benefit_dict['channel'])
            if not benefit_list:
                benefit_dict = dict()
                benefit_dict['couponCode'] = existing_voucher['voucher'].code
                benefit_dict['items'] = item_id_list
                benefit_dict['type'] = existing_voucher['voucher'].type
                benefit_dict['paymentMode'] = rule.criteria_obj.payment_modes
                benefit_dict['channel'] = [Channels(c).value for c in rule.criteria_obj.channels]
                benefit_dict['custom'] = existing_voucher['voucher'].custom
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
    total_agent_discount = 0.0
    total_cashback = 0.0
    total_agent_cashback = 0.0
    products_list = list()
    for item in products_dict:
        product_dict = products_dict[item]
        products_list.append(product_dict)
        total_discount += product_dict['discount']
        total_agent_discount += product_dict['agent_discount']
        total_cashback += product_dict['cashback']
        total_agent_cashback += product_dict['agent_cashback']
        product_dict['discount'] = round(product_dict['discount'], 2)
        product_dict['agent_discount'] = round(product_dict['agent_discount'], 2)
        product_dict['cashback'] = round(product_dict['cashback'], 2)
        product_dict['agent_cashback'] = round(product_dict['agent_cashback'], 2)

    for a_benefit in benefits_list:
        if a_benefit['type'] is VoucherType.regular_coupon.value\
                and a_benefit.get('amount_actual'):
            a_benefit['amount'] = a_benefit['amount_actual']
            del a_benefit['amount_actual']

    total_discount = round(total_discount, 2)
    total_agent_discount = round(total_agent_discount, 2)
    total_cashback = round(total_cashback, 2)
    total_agent_cashback = round(total_agent_cashback, 2)

    response_dict = dict()

    response_dict['products'] = products_list
    response_dict['benefits'] = benefits_list
    response_dict['totalDiscount'] = total_discount
    response_dict['totalCashback'] = total_cashback
    response_dict['totalAgentDiscount'] = total_agent_discount
    response_dict['totalAgentCashback'] = total_agent_cashback
    if hasattr(order, 'check_payment_mode') and order.check_payment_mode:
            response_dict['paymentMode'] = order.payment_mode
    else:
        response_dict['paymentMode'] = payment_modes_list
    response_dict['channel'] = channels_list
    response_dict['couponCodes'] = [existing_voucher['voucher'].code for existing_voucher in order.existing_vouchers]
    return response_dict


def create_regular_voucher(args, get_criteria_kwargs_callback):
    rule_id_list, rule_list = create_and_save_rule_list(args, get_criteria_kwargs_callback)
    assert(len(rule_list) == len(rule_id_list))
    if not rule_id_list:
        return create_error_response(400, u'Unknown Exception')

    args['from'] = get_utc_timezone_unaware_date_object(args.get('from'))
    args['to'] = get_utc_timezone_unaware_date_object(args.get('to'))

    from validate import validate_for_create_voucher

    success, error = validate_for_create_voucher(args)
    if not success:
        return create_error_response(400, error)

    success_list, error_list = save_vouchers(args, rule_id_list)

    for s in success_list:
        del s['id']
    return create_success_response(success_list, error_list)
