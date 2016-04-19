from api import rule_api, voucher_api
from flask import jsonify


@voucher_api.app_errorhandler(422)
def handle_error(error):
    key_list = list()
    for key in error.data['messages'].keys():
        key_list.append(key)
    rv = {
        'success': False,
        'error': {
            'code': 422,
            'error': u'Invalid value for the following keys {}'.format(key_list)
        },
        'errors': [u'Invalid value for the following keys {}'.format(key_list)]
    }
    res = jsonify(rv)
    res.status_code = 422
    return res
