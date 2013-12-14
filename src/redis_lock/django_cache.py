from redis_cache.cache import RedisCache as PlainRedisCache
from redis_lock import Lock


class RedisCache(PlainRedisCache):
    def lock(self, key, expire=None):
        try:
            client = self.raw_client
        except Exception as exc:
            raise NotImplementedError("RedisCache doesn't have a raw client: %r. Use 'redis_cache.client.DefaultClient' as the CLIENT_CLASS !" % exc)
        return Lock(client, key, expire=expire)
