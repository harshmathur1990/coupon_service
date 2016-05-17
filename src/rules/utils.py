import datetime
import importlib
import json
import logging
import uuid
from datetime import timedelta

import croniter
from dateutil import parser

from lib.utils import is_between, get_num_from_str, create_error_response
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
    from config import method_dict
    get_rule_criteria_blacklist_criteria_and_benefits = getattr(
        importlib.import_module(
            method_dict.get('get_rule_criteria_blacklist_criteria_and_benefits')['package']),
        method_dict.get('get_rule_criteria_blacklist_criteria_and_benefits')['attribute'])

    rule_criteria, rule_blacklist_criteria, benefits = get_rule_criteria_blacklist_criteria_and_benefits(data)
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
        from config import method_dict
        callback = getattr(
            importlib.import_module(
                method_dict.get('check_auto_benefit_exclusivity')['package']),
            method_dict.get('check_auto_benefit_exclusivity')['attribute'])
        success, error_list = voucher.update(update_dict, db, callback)
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


def make_transaction_log_entry(args):
    success, error = VoucherTransactionLog.make_transaction_log_entry(args)
    if not success:
        rv = create_error_response(400, error)
    else:
        rv = {'success': success}
    return rv
