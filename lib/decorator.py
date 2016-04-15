import time
import functools
import logging
import json
from flask import Response
from flask import request
from utils import unauthenticated, is_logged_in
logger = logging.getLogger(__name__)


def logtime(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        start = time.time()
        rv = f(*args, **kwargs)
        logger.info('Time taken (for args %s) = %s', args, time.time() - start)
        return rv
    return wrapped


def jsonify(f):
    # always make your responses in this format
    # {
    #   success: True/False,
    #   error: {
    #     code: 400,
    #   },
    #   data: {
    #   }
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        start = time.time()
        rv = f(*args, **kwargs)
        status_code = 200
        if not rv.get('success', False):
            status_code = rv.get('error', dict()).get('code', 500)
        resp = Response(
            response=json.dumps(rv), status=status_code,
            mimetype="application/json")
        logger.info(u'URL: {} Arguments: {} Keyword Arguments: {} Body: {} Returned: {} Total time taken: {}'.format(
            request.url_rule, args, kwargs, request.get_data(), rv, time.time() - start))
        return resp
    return wrapped


def logrequest(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        rv = f(*args, **kwargs)
        logger.info("Arguments = %s Returned %s" % (kwargs, rv))
        return rv
    return wrapped


def check_login(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        agent_name = request.headers.get('X-API-USER', None)
        authorization = request.headers.get('X-API-TOKEN', 'Acdlsdksl')
        if authorization and is_logged_in(agent_name, authorization):
            return method(*args, **kwargs)
        else:
            return unauthenticated()
    return wrapper
