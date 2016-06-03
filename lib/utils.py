import requests
import logging
import time
import pytz
import croniter
from src.enums import SchedulerType
from src.rules.user import User
from src.sqlalchemydb import CouponsAlchemyDB
from flask import request
from dateutil import parser
import json

logger = logging.getLogger(__name__)


def is_timezone_aware(datetime_obj):
    if datetime_obj.tzinfo is not None and datetime_obj.tzinfo.utcoffset(datetime_obj) is not None:
        return True
    return False


def get_intersection_of_lists(list1, list2, key=None):
    if not key:
        return [l for l in list1 if l in list2]
    else:
        return [l[key] for l in list1 if l in list2]


def make_api_call(url, method='GET', body=None, headers=dict(), params=dict()):
    # body must be a json serializable dict
    start = time.time()
    if method == 'GET':
        response = requests.get(url=url, headers=headers, params=params)
    elif method == 'POST':
        response = requests.post(url=url, headers=headers, json=body, params=params)
    elif method == 'PUT':
        response = requests.post(url=url, headers=headers, json=body, params=params)
    else:
        raise Exception(u'Method {} not supported'.format(method))
    logger.info(u'Url: {}, method: {}, headers: {}, Request Body: {} Status Code: {} Response Body: {} Total Time Taken: {}'.format(
            url, method, headers, body, response.status_code, response.text, time.time() - start))
    return response


def create_success_response(success_list, error_list=list(), success=True):
    rv = {
        'success': success,
        'data': {
            'success_list': success_list,
            'error_list': error_list
        }
    }
    return rv


def create_error_response(error_code, error_msg=''):
    rv = {
        'success': False,
        'error': {
            'code': error_code,
        }
    }
    if isinstance(error_msg, list):
        rv['error']['error'] = ','.join(error_msg)
        rv['errors'] = error_msg
    else:
        rv['errors'] = [error_msg]
        rv['error']['error'] = error_msg
    return rv


def unauthenticated():
    return create_error_response(401, u'Unauthenticated Client')


def is_logged_in(agent_name, authorization):
    # return True
    authenticated = False
    db = CouponsAlchemyDB()
    token = db.find_one("tokens", **{'token': authorization, 'agent_name': agent_name})
    if token:
        user_dict = dict()
        user_dict['agent_id'] = token['agent_id']
        user_dict['agent_name'] = token['agent_name']
        user = User(**user_dict)
        setattr(request, 'user', user)
        authenticated = True
    return authenticated


def get_agent_id():
    agent_id = None
    try:
        agent_id = request.user.agent_id
    except AttributeError:
        pass
    return agent_id


def is_valid_cron_string(value):
    success = False
    try:
        cron = croniter.croniter(value)
        success = True
    except:
        pass
    return success


def is_valid_duration_string(value):
    success = False
    try:
        duration_list = value.split(':')
        if 5 == len(duration_list):
            error = False
            week = int(duration_list[0]) if duration_list[0] != '' else 0
            days = int(duration_list[1]) if duration_list[1] != '' else 0
            hours = int(duration_list[2]) if duration_list[2] != '' else 0
            minutes = int(duration_list[3]) if duration_list[3] != '' else 0
            seconds = int(duration_list[4]) if duration_list[4] != '' else 0
            if week and week < 0:
                error = True
            if days and days < 0:
                error = True
            if hours and (hours >= 24 or hours < 0):
                error = True
            if seconds and (seconds >= 60 or seconds < 0):
                error = True
            if minutes and (minutes >= 60 or minutes < 0):
                error = True
            if not error:
                success = True
    except Exception:
        pass
    return success


def date_validator(value):
    success = False
    try:
        parser.parse(value)
        success = True
    except:
        pass
    return success


def schedule_validate_method(type):
    return {
        SchedulerType.daily.value: date_validator,
        SchedulerType.exact.value: date_validator,
        SchedulerType.cron.value: is_valid_cron_string
    }.get(type, SchedulerType.daily.value)


def is_valid_schedule_object(args):
    success = True
    if args.get('schedule'):
        error = False
        for schedule in args.get('schedule'):
            type = schedule.get('type')
            success = schedule_validate_method(type)(schedule.get('value'))
            if not success:
                error = True
                break
        if not error:
            success = True
    return success


def length_validator(value, length_limit, type='object'):
    if type == 'object':
        value_string = json.dumps(value)
    else:
        value_string = value
    if len(value_string) >= length_limit:
        return False
    return True


def handle_unprocessable_entity(e):
    key_list = list()
    for key in e.data['messages'].keys():
        key_list.append(key)
    rv = {
        'success': False,
        'error': {
            'code': 422,
            'error': u'Invalid value for the following keys {}'.format(key_list)
        },
        'errors': [u'Invalid value for the following keys {}'.format(key_list)]
    }
    return rv


def get_utc_timezone_unaware_date_object(date_object):
    if not is_timezone_aware(date_object):
        return date_object
    date_object = date_object.astimezone(pytz.UTC)
    date_object = date_object.replace(tzinfo=None)
    return date_object


def is_between(this_date, start_date, end_date):
    if this_date > end_date or this_date < start_date:
        return False
    return True


def get_num_from_str(str):
    str = str.strip()
    try:
        if len(str) is 0 or str is None:
            return 0
        else:
            return int(str)
    except Exception as exp:
        return 0