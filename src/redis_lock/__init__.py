from logging import getLogger
logger = getLogger(__name__)

from os import urandom
from hashlib import sha1

from redis import StrictRedis
from redis.exceptions import NoScriptError

__version__ = "1.0.0"

UNLOCK_SCRIPT = b"""
    if redis.call("get", KEYS[1]) == ARGV[1] then
        redis.call("lpush", KEYS[2], 1)
        return redis.call("del", KEYS[1])
    else
        return 0
    end
"""
UNLOCK_SCRIPT_HASH = sha1(UNLOCK_SCRIPT).hexdigest()


class cached_property(object):
    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class Lock(object):
    def __init__(self, redis_client, name, expire=None):
        assert isinstance(redis_client, StrictRedis)
        self._client = redis_client
        self._expire = expire if expire is None else int(expire)
        self._tok = None
        self._name = 'lock:'+name
        self._signal = 'lock-signal:'+name

    def reset(self):
        """
        Forcibly deletes the lock. Use this with care.
        """
        self._client.delete(self._name)
        self._client.delete(self._signal)

    @cached_property
    def token(self):
        return urandom(16)

    def acquire(self, blocking=True):
        logger.debug("Getting %r ...", self._name)

        if self._tok is None:
            self._tok = self.token
        else:
            raise RuntimeError("Already aquired from this Lock instance.")

        busy = True
        while busy:
            busy = not self._client.set(self._name, self._tok, nx=True, ex=self._expire)
            if busy:
                if blocking:
                    self._client.blpop(self._signal, self._expire or 0)
                else:
                    logger.debug("Failed to get %r.", self._name)
                    return False

        logger.debug("Got lock for %r.", self._name)
        return True

    def __enter__(self):
        assert self.acquire(blocking=True)
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        logger.debug("Releasing %r.", self._name)
        try:
            self._client.evalsha(UNLOCK_SCRIPT_HASH, 2, self._name, self._signal, self._tok)
        except NoScriptError:
            logger.warn("UNLOCK_SCRIPT not cached.")
            self._client.eval(UNLOCK_SCRIPT, 2, self._name, self._signal, self._tok)
    release = __exit__


def reset_all(redis_client):
    """
    Forcibly deletes all locks if its remains (like a crash reason). Use this with care.
    """
    for lock_key in redis_client.keys('lock:*'):
        redis_client.delete(lock_key)
    for lock_key in redis_client.keys('lock-signal:*'):
        redis_client.delete(lock_key)
