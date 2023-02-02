import sys
import threading
import time
from base64 import b64encode
from logging import getLogger
from os import urandom
from queue import SimpleQueue

from redis import StrictRedis

__version__ = '3.7.0'

loggers = {
    k: getLogger(".".join((__name__, k)))
    for k in [
        "acquire",
        "refresh.thread.start",
        "refresh.thread.stop",
        "refresh.thread.exit",
        "refresh.thread",
        "refresh.start",
        "refresh.shutdown",
        "refresh.exit",
        "release",
    ]
}

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
else:
    text_type = unicode  # noqa
    binary_type = str


# Check if the id match. If not, return an error code.
UNLOCK_SCRIPT = b"""
    if redis.call("get", KEYS[1]) ~= ARGV[1] then
        return 1
    else
        redis.call("del", KEYS[1])
        return 0
    end
"""

# Covers both cases when key doesn't exist and doesn't equal to lock's id
EXTEND_SCRIPT = b"""
    if redis.call("get", KEYS[1]) ~= ARGV[1] then
        return 1
    elseif redis.call("ttl", KEYS[1]) < 0 then
        return 2
    else
        redis.call("expire", KEYS[1], ARGV[2])
        return 0
    end
"""

RESET_ALL_SCRIPT = b"""
    local locks = redis.call('keys', 'lock:*')
    local signal
    for _, lock in pairs(locks) do
        signal = 'lock-signal:' .. string.sub(lock, 6)
        redis.call('del', signal)
        redis.call('lpush', signal, 1)
        redis.call('expire', signal, 1)
        redis.call('del', lock)
    end
    return #locks
"""


class AlreadyAcquired(RuntimeError):
    pass


class NotAcquired(RuntimeError):
    pass


class AlreadyStarted(RuntimeError):
    pass


class TimeoutNotUsable(RuntimeError):
    pass


class InvalidTimeout(RuntimeError):
    pass


class TimeoutTooLarge(RuntimeError):
    pass


class NotExpirable(RuntimeError):
    pass


lock_to_extend_time = dict()
add_lock_extend_queue = SimpleQueue()
MIN_RENEW_THRESHOLD_SECS = 6


def safe_extend_lock_time(lock):
    try:
        lock_to_extend_time[lock] = time.time() + lock.lock_renewal_interval
        return True
    except TypeError:
        return False


def extend_locks(logger):
    to_remove_locks = list()
    for lock, extend_time in lock_to_extend_time.items():
        if extend_time <= time.time():
            try:
                if lock.lock_renewal_interval:
                    lock.extend()
                    success = safe_extend_lock_time(lock)
                    if not success:
                        to_remove_locks.append(lock)
                else:
                    to_remove_locks.append(lock)
            except NotAcquired as e:
                if lock.lock_renewal_interval:
                    logger.error("Got NotAcquired on extend while renewal is still active %s", e)
                to_remove_locks.append(lock)
            except Exception as e:
                logger.exception("Got exception on extend %s", e)
                if lock.lock_renewal_interval:
                    success = safe_extend_lock_time(lock)
                    if not success:
                        to_remove_locks.append(lock)

    return to_remove_locks


def start_locking_thread():
    logger = loggers["refresh.thread"]
    while True:
        try:
            to_remove_locks = extend_locks(logger)

            for lock in to_remove_locks:
                lock_to_extend_time.pop(lock)

            while not add_lock_extend_queue.empty():
                lock = add_lock_extend_queue.get_nowait()
                if lock:
                    safe_extend_lock_time(lock)

            time.sleep(0.5)
        except Exception as e:
            logger.exception("Got exception on iter %s", e)


lock_thread = threading.Thread(target=start_locking_thread)
lock_thread.setDaemon(True)
lock_thread.start()


class Lock(object):
    """
    A Lock context manager implemented via redis SETNX and one extending thread.
    """
    unlock_script = None
    extend_script = None
    reset_all_script = None

    def __init__(self, redis_client, name, expire=None, id=None, auto_renewal=False, strict=True):
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

            Note that if you specify this then the lock is marked as "held". Acquires
            won't be possible.
        :param auto_renewal:
            If set to ``True``, Lock will automatically renew the lock so that it
            doesn't expire for as long as the lock is held (acquire() called
            or running in a context manager).

            Implementation note: Renewal will happen using a daemon thread with
            an interval of ``expire*2/3``. If wishing to use a different renewal
            time, subclass Lock, call ``super().__init__()`` then set
            ``self._lock_renewal_interval`` to your desired interval.
        :param strict:
            If set ``True`` then the ``redis_client`` needs to be an instance of ``redis.StrictRedis``.
        :param signal_expire:
            Advanced option to override signal list expiration in milliseconds. Increase it for very slow clients. Default: ``1000``.
        """
        if strict and not isinstance(redis_client, StrictRedis):
            raise ValueError("redis_client must be instance of StrictRedis. "
                             "Use strict=False if you know what you're doing.")
        if auto_renewal and expire is None:
            raise ValueError("Expire may not be None when auto_renewal is set")

        self._client = redis_client

        if expire:
            expire = int(expire)
            if expire < 0:
                raise ValueError("A negative expire is not acceptable.")
        else:
            expire = None
        self._expire = expire

        if id is None:
            self._id = b64encode(urandom(18)).decode('ascii')
        elif isinstance(id, binary_type):
            try:
                self._id = id.decode('ascii')
            except UnicodeDecodeError:
                self._id = b64encode(id).decode('ascii')
        elif isinstance(id, text_type):
            self._id = id
        else:
            raise TypeError("Incorrect type for `id`. Must be bytes/str not %s." % type(id))
        self._name = name
        self.lock_renewal_interval = self.get_renewal_interval(auto_renewal)

        self.register_scripts(redis_client)

    def get_renewal_interval(self, auto_renewal):
        if not auto_renewal:
            return
        if self._expire < 10:
            raise Exception("Expiration is too low to ensure renewal")
        return min(self._expire * 0.5, self._expire - MIN_RENEW_THRESHOLD_SECS)

    @classmethod
    def register_scripts(cls, redis_client):
        global reset_all_script
        if reset_all_script is None:
            reset_all_script = redis_client.register_script(RESET_ALL_SCRIPT)
            cls.unlock_script = redis_client.register_script(UNLOCK_SCRIPT)
            cls.extend_script = redis_client.register_script(EXTEND_SCRIPT)
            cls.reset_all_script = redis_client.register_script(RESET_ALL_SCRIPT)

    @property
    def _held(self):
        return self.id == self.get_owner_id()

    def reset(self):
        """
        Forcibly deletes the lock. Use this with care.
        """
        self._client.delete(self._name)

    @property
    def id(self):
        return self._id

    def get_owner_id(self):
        owner_id = self._client.get(self._name)
        if isinstance(owner_id, binary_type):
            owner_id = owner_id.decode('ascii', 'replace')
        return owner_id

    def acquire(self):
        """
        :param blocking:
            Boolean value specifying whether lock should be blocking or not.
        :param timeout:
            An integer value specifying the maximum number of seconds to block.
        """
        logger = loggers["acquire"]

        logger.debug("Getting %r ...", self._name)

        if self._held:
            raise AlreadyAcquired("Already acquired from this Lock instance.")

        is_locked = not self._client.set(self._name, self._id, nx=True, ex=self._expire)
        if is_locked:
            logger.warning("Failed to get %r.", self._name)
            return False

        logger.info("Got lock for %r.", self._name)
        if self.lock_renewal_interval is not None:
            add_lock_extend_queue.put_nowait(self)
        return True

    def extend(self, expire=None):
        """Extends expiration time of the lock.

        :param expire:
            New expiration time. If ``None`` - `expire` provided during
            lock initialization will be taken.
        """
        if expire:
            expire = int(expire)
            if expire < 0:
                raise ValueError("A negative expire is not acceptable.")
        elif self._expire is not None:
            expire = self._expire
        else:
            raise TypeError(
                "To extend a lock 'expire' must be provided as an "
                "argument to extend() method or at initialization time."
            )

        error = self.extend_script(client=self._client, keys=(self._name,), args=(self._id, expire))
        if error == 1:
            raise NotAcquired("Lock %s is not acquired or it already expired." % self._name)
        elif error == 2:
            raise NotExpirable("Lock %s has no assigned expiration time" % self._name)
        elif error:
            raise RuntimeError("Unsupported error code %s from EXTEND script" % error)

    def release(self):
        """Releases the lock, that was acquired with the same object.

        .. note::

            If you want to release a lock that you acquired in a different place you have two choices:

            * Use ``Lock("name", id=id_from_other_place).release()``
            * Use ``Lock("name").reset()``
        """
        if self.lock_renewal_interval is not None:
            self.lock_renewal_interval = None
        # if self._lock_renewal_thread is not None:
        #     self._stop_lock_renewer()
        loggers["release"].debug("Releasing %r.", self._name)
        error = self.unlock_script(client=self._client, keys=(self._name,), args=(self._id,))
        if error == 1:
            raise NotAcquired("Lock %s is not acquired or it already expired." % self._name)
        elif error:
            raise RuntimeError("Unsupported error code %s from EXTEND script." % error)

    def locked(self):
        """
        Return true if the lock is acquired.

        Checks that lock with same name already exists. This method returns true, even if
        lock have another id.
        """
        return self._client.exists(self._name) == 1


reset_all_script = None


def reset_all(redis_client):
    """
    Forcibly deletes all locks if its remains (like a crash reason). Use this with care.

    :param redis_client:
        An instance of :class:`~StrictRedis`.
    """
    Lock.register_scripts(redis_client)

    reset_all_script(client=redis_client)  # noqa
