import threading
from logging import getLogger
from os import urandom
from hashlib import sha1

from redis import StrictRedis
from redis.exceptions import NoScriptError

__version__ = "2.1.0"

logger = getLogger(__name__)

UNLOCK_SCRIPT = b"""
    if redis.call("get", KEYS[1]) == ARGV[1] then
        redis.call("del", KEYS[2])
        redis.call("lpush", KEYS[2], 1)
        return redis.call("del", KEYS[1])
    else
        return 0
    end
"""
UNLOCK_SCRIPT_HASH = sha1(UNLOCK_SCRIPT).hexdigest()


class AlreadyAcquired(RuntimeError):
    pass


class NotAcquired(RuntimeError):
    pass


class AlreadyStarted(RuntimeError):
    pass


class Lock(object):
    """
    A Lock context manager implemented via redis SETNX/BLPOP.
    """

    def __init__(self, redis_client, name, expire=None, id=None, refresh_interval=-1):
        """
        :param redis_client:
            An instance of :class:`~StrictRedis`.
        :param name:
            The name (redis key) the lock should have.
        :param expire:
            The lock expiry time in seconds. If left at the default (None)
            the lock will not expire.
        :param id:
            The ID (redis value) the lock should have. A random value is
            generated when left at the default.
        :param refresh_interval:
            If set to a value greater than 0, automatically refresh the
            lock every `refresh_interval` seconds using a separate thread.
        """
        assert isinstance(redis_client, StrictRedis)
        self._client = redis_client
        self._expire = expire if expire is None else int(expire)
        self._id = urandom(16) if id is None else id
        self._held = False
        self._name = 'lock:'+name
        self._signal = 'lock-signal:'+name
        self._lock_refresh_interval = refresh_interval
        self._lock_refresh_thread = None

    def reset(self):
        """
        Forcibly deletes the lock. Use this with care.
        """
        self._client.delete(self._name)
        self._client.delete(self._signal)

    @property
    def id(self):
        return self._id

    def get_owner_id(self):
        return self._client.get(self._name)

    def acquire(self, blocking=True):
        logger.debug("Getting %r ...", self._name)

        if self._held:
            raise AlreadyAcquired("Already aquired from this Lock instance.")

        busy = True
        while busy:
            busy = not self._client.set(self._name, self._id, nx=True, ex=self._expire)
            if busy:
                if blocking:
                    self._client.blpop(self._signal, self._expire or 0)
                else:
                    logger.debug("Failed to get %r.", self._name)
                    return False

        logger.debug("Got lock for %r.", self._name)
        self._held = True
        if self._lock_refresh_interval > 0:
            self._start_lock_refresher()
        return True

    def _lock_refresher(self, interval):
        """
        Refresh the lock key in redis every `interval` seconds as long as
        `self._lock_refresh_thread.should_exit` is False.
        """
        log = getLogger("%s.lock_refresher" % __name__)
        while not self._lock_refresh_thread.wait_for_exit_request(timeout=interval):
            log.debug("Refreshing lock")
            self._client.set(self._name, self._id, xx=True, ex=self._expire)
        log.debug("Exit requested, stopping lock refreshing")

    def _start_lock_refresher(self):
        """Start the lock refresher"""
        if self._lock_refresh_thread is not None:
            raise AlreadyStarted("Lock refresh thread already started")

        logger.debug(
            "Starting thread to refresh lock every %s seconds",
            self._lock_refresh_interval
        )
        self._lock_refresh_thread = InterruptableThread(
            group=None,
            target=self._lock_refresher,
            kwargs={'interval': self._lock_refresh_interval}
        )
        self._lock_refresh_thread.setDaemon(True)
        self._lock_refresh_thread.start()

    def _stop_lock_refresher(self):
        """Stop the lock refresher"""
        if self._lock_refresh_thread is None or not self._lock_refresh_thread.is_alive():
            return
        logger.debug("Signalling the lock refresher to stop")
        self._lock_refresh_thread.request_exit()
        self._lock_refresh_thread.join()
        self._lock_refresh_thread = None
        logger.debug("Lock refresher has stopped")

    def __enter__(self):
        assert self.acquire(blocking=True)
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None, force=False):
        if not (self._held or force):
            raise NotAcquired("This Lock instance didn't acquire the lock.")
        if self._lock_refresh_thread is not None:
            self._stop_lock_refresher()
        logger.debug("Releasing %r.", self._name)
        try:
            self._client.evalsha(UNLOCK_SCRIPT_HASH, 2, self._name, self._signal, self._id)
        except NoScriptError:
            logger.warn("UNLOCK_SCRIPT not cached.")
            self._client.eval(UNLOCK_SCRIPT, 2, self._name, self._signal, self._id)
        self._held = False
    release = __exit__


class InterruptableThread(threading.Thread):
    """
    A Python thread that can be requested to stop by calling request_exit()
    on it.

    Code running inside this thread should periodically check the
    `should_exit` property (or use wait_for_exit_request) on the thread
    object and stop further processing once it returns True.
    """
    def __init__(self, *args, **kwargs):
        self._should_exit = threading.Event()
        super(InterruptableThread, self).__init__(*args, **kwargs)

    def request_exit(self):
        """
        Signal the thread that it should stop performing more work and exit.
        """
        self._should_exit.set()

    @property
    def should_exit(self):
        return self._should_exit.isSet()

    def wait_for_exit_request(self, timeout=None):
        """
        Wait until the thread has been signalled to exit.

        If timeout is specified (as a float of seconds to wait) then wait
        up to this many seconds before returning the value of `should_exit`.
        """
        return self._should_exit.wait(timeout)


def reset_all(redis_client):
    """
    Forcibly deletes all locks if its remains (like a crash reason). Use this with care.
    """
    for lock_key in redis_client.keys('lock:*'):
        redis_client.delete(lock_key)
    for lock_key in redis_client.keys('lock-signal:*'):
        redis_client.delete(lock_key)
