from redis_cache.cache import RedisCache as PlainRedisCache
from redis_lock import Lock


class RedisCache(PlainRedisCache):
    def lock(self, key, expire=None):
        return Lock(self.client, key, expire=expire)
