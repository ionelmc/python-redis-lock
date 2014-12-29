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

    def reset_all(self):
        """
        Forcibly deletes all locks if its remains (like a crash reason). Use this with care.
        """
        reset_all(self.__client)
