import grequests
import logging
import time
import croniter
from src.rules.user import User
from src.sqlalchemydb import CouponsAlchemyDB
from flask import request

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


def make_api_call(urls, headers=dict()):
    rs = (grequests.get(u, headers=headers) for u in urls)
    start = time.time()
    response_list = grequests.map(rs)
    for response, url in zip(response_list, urls):
        logger.info(u'Url: {}, headers: {}, Status Code: {} Response Body: {} Total Time Taken: {}'.format(
            url, headers, response.status_code, response.text, time.time() - start))
    return response_list


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


def is_valid_curl_string(value):
    import ipdb;ipdb.set_trace()
    success = False
    try:
        cron = croniter.croniter(value)
        success = True
    except:
        pass
    return success


def is_valid_duration_string(value):
    import ipdb;ipdb.set_trace()
    success = False
    try:
        duration_list = value.split(':')
        if 5 == len(duration_list):
            error = False
            week = duration_list[0]
            days = duration_list[1]
            hours = duration_list[2]
            minutes = duration_list[3]
            seconds = duration_list[4]
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
