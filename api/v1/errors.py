from api import rule_api, voucher_api
from flask import jsonify


@voucher_api.app_errorhandler(422)
def handle_error(error):
    rv = {
        'success': False,
        'error': {
            'code': 422,
            'error': error.data['messages']
        }
    }
    res = jsonify(rv)
    res.status_code = 422
    return res
