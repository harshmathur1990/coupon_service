import grequests


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
    return grequests.map(rs)


def create_success_response(success_list, error_list=list()):
    rv = {
        'success': True,
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
            'error': error_msg
        }
    }
    return rv