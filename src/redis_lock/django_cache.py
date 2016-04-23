from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django_redis.cache import RedisCache as PlainRedisCache

from redis_lock import Lock
from redis_lock import reset_all


class RedisCache(PlainRedisCache):

    @property
    def __client(self):
        try:
            return self.client.get_client()
        except Exception as exc:
            raise NotImplementedError(
                "RedisCache doesn't have a raw client: %r. "
                "Use 'redis_cache.client.DefaultClient' as the CLIENT_CLASS !" % exc
            )

    def lock(self, key, expire=None, id=None):
        return Lock(self.__client, key, expire=expire, id=id)

    def get_or_set_locked(self, key, value_creator, version=None,
                          expire=None, id=None, lock_key=None,
                          timeout=DEFAULT_TIMEOUT):
        """
        Fetch a given key from the cache. If the key does not exist, the key is added and
        set to the value returned when calling `value_creator`. The creator function
        is invoked inside of a lock.
        """
        # As users might put `None` into the cache, we need something
        # uniquely recognizable for our `default` argument to `.get`.
        not_set = object()

        if lock_key is None:
            lock_key = '{0}.set-lock'.format(key)

        val = self.get(key, version=version, default=not_set)
        if val is not not_set:
            return val
        else:
            with self.lock(lock_key, expire=expire, id=id):
                # Was the value set while we were trying to acquire the lock?
                val = self.get(key, version=version, default=not_set)
                if val is not not_set:
                    return val

                # Nope, create value now.
                val = value_creator()
                self.set(key, val, timeout=timeout, version=version)
                return val

    def reset_all(self):
        """
        Forcibly deletes all locks if its remains (like a crash reason). Use this with care.
        """
        reset_all(self.__client)
