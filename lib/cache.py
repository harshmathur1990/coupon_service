import redis
import pickle
import logging

from config import RULESREDISDB, RULESREDISHOST, RULESREDISPORT

rules_pool = redis.ConnectionPool(
    host=RULESREDISHOST, port=RULESREDISPORT, db=RULESREDISDB)
cache_type = {
    'rules': rules_pool
}
logger = logging.getLogger()


def set(key, value, ctype='rules', ex=None, px=None, nx=False, xx=False):
    """
    Set the value at key ``name`` to ``value``

    ``ex`` sets an expire flag on key ``name`` for ``ex`` seconds.

    ``px`` sets an expire flag on key ``name`` for ``px`` milliseconds.

    ``nx`` if set to True, set the value at key ``name`` to ``value`` if it
        does not already exist.

    ``xx`` if set to True, set the value at key ``name`` to ``value`` if it
        already exists.
    """
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    return r.set(key, pickle.dumps(value), ex, px, nx, xx)


def get(key, ctype='rules'):
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    pickled_value = r.get(key)
    if pickled_value is None:
        return None
    try:
        result = pickle.loads(pickled_value)
    except ImportError as e:
        logger.info(e)
        return None
    except Exception as e:
        logger.exception(e)
        return None

    return result


def exists(key, ctype='rules'):
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    return r.exists(key)


def delete(key, ctype='rules'):
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    return r.delete(key)
