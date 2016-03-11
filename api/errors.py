from . import api
from flask import jsonify


@api.app_errorhandler(422)
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
