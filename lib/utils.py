import grequests
import logging
import time

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


def is_logged_in(agent_id, authorization):
    return True
    # authenticated = False
    # db = CouponsAlchemyDB()
    # token = db.find_one("tokens", **{'token': authorization, 'agent_id': agent_id})
    # if token:
    #     user = dict()
    #     user['agent_id'] = token['agent_id']
    #     setattr(request, 'user', user)
    #     authenticated = True
    # return authenticated
