from api import voucher_api
from flask import request
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


@voucher_api.app_errorhandler(422)
def handle_error(error):
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
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


@voucher_api.app_errorhandler(500)
def handle_error(error):
    logger.exception(error)
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    rv = {
        'success': False,
        'error': {
            'code': 500,
            'error': u'Unknown Error, Please contact tech support'
        },
        'errors': [u'Unknown Error, Please contact tech support']
    }
    res = jsonify(rv)
    res.status_code = 500
    return res
