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


def set(key, value, ctype='rules'):
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    return r.set(key, pickle.dumps(value))


def get(key, ctype='rules'):
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    pickled_value = r.get(key)
    if pickled_value is None:
        return None
    result = pickle.loads(pickled_value)
    return result


def exists(key, ctype='rules'):
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    return r.exists(key)


def delete(key, ctype='rules'):
    pool = cache_type.get(ctype)
    r = redis.StrictRedis(connection_pool=pool)
    return r.delete(key)
