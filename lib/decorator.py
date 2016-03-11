import time
import functools
import logging
import json
from flask import Response
from webargs import core, ValidationError
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
        try:
            rv = f(*args, **kwargs)
            status_code = 200
            if not rv.get('success', False):
                status_code = rv.get('error', dict()).get('code', 500)
            resp = Response(
                response=json.dumps(rv), status=status_code,
                mimetype="application/json")
        except Exception as e:
            logger.exception('Error while processing request')
            resp = Response(response=json.dumps({'message': str(e)}), status=500,
                            mimetype="application/json")
            logger.info('Total time taken = %s', time.time() - start)
        return resp
    return wrapped


def logrequest(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        rv = f(*args, **kwargs)
        logger.info("Arguments = %s Returned %s" % (kwargs, rv))
        return rv
    return wrapped

