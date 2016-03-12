from . import rule_api, voucher_api
from flask import jsonify


@voucher_api.app_errorhandler(422)
@rule_api.app_errorhandler(422)
def handle_error(error):
    rv = {
        'success': False,
        'error': {
            'code': 400,
            'error': error.data['messages']
        }
    }
    res = jsonify(rv)
    res.status_code = 400
    return res
