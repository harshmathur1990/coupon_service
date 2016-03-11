from . import api
from flask import jsonify


@api.errorhandler(422)
def handle_error(error):
    rv = {
        'success': False,
        'error': {
            'code': 400,
            'error': error.data['messages']
        }
    }
    return jsonify(rv), 400
