from typing import Optional

from django.core.cache.backends.dummy import DummyCache
from django.core.cache.backends.redis import RedisCache


class TacticalRedisCache(RedisCache):
    def delete_many_pattern(self, pattern: str, version: Optional[int] = None) -> None:
        keys = self._cache.get_client().keys(f":{version or 1}:{pattern}")

        if keys:
            self._cache.delete_many(keys)

    # just for debugging
    def show_everything(self, version: Optional[int] = None) -> list[bytes]:
        return self._cache.get_client().keys(f":{version or 1}:*")

    def iter_keys_pattern(self, pattern: str, version: Optional[int] = None):
        client = self._cache.get_client()
        yield from client.scan_iter(match=f":{version or 1}:{pattern}")

    def raw_ttl(self, key: bytes) -> int:
        return self._cache.get_client().ttl(key)


class TacticalDummyCache(DummyCache):
    def delete_many_pattern(self, pattern: str, version: Optional[int] = None) -> None:
        return None
