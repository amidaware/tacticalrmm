#!/usr/bin/env python3

from typing import Optional, Callable, Any

from django.core.cache.backends.dummy import DummyCache
from django.core.cache.backends.redis import (
    RedisCache,
)  # noqa: Required Django dependency


class TacticalRedisCache(RedisCache):
    """
    An extension of the Django RedisCache with additional methods for Tactical RMM.
    This class was previously used for pub/sub but has been replaced with direct Redis access.
    It is kept for backward compatibility.
    """

    def delete_many_pattern(self, pattern: str, version: Optional[int] = None) -> None:
        keys = self._cache.get_client().keys(f":{version or 1}:{pattern}")

        if keys:
            self._cache.delete_many(keys)

    # just for debugging
    def show_everything(self, version: Optional[int] = None) -> list[bytes]:
        return self._cache.get_client().keys(f":{version or 1}:*")

    def publish(self, channel: str, message: Any) -> int:
        """
        Publish a message to a Redis channel.

        Args:
            channel: The channel name to publish to
            message: The message to publish (can be string or serialized JSON)

        Returns:
            Number of subscribers that received the message
        """
        client = self._cache.get_client()
        return client.publish(channel, message)

    def subscribe(
        self, channels: list[str], callback: Callable[[str, bytes], None]
    ) -> None:
        """
        Subscribe to Redis channels with a callback function.

        This is a blocking call that will run indefinitely, processing messages
        as they are received. The callback function will be called for each message.

        Args:
            channels: List of channel names to subscribe to
            callback: Function that takes (channel, message) arguments
        """
        client = self._cache.get_client()
        pubsub = client.pubsub()
        pubsub.subscribe(*channels)

        for message in pubsub.listen():
            if message["type"] == "message":
                callback(message["channel"], message["data"])


class TacticalDummyCache(DummyCache):
    def delete_many_pattern(self, pattern: str, version: Optional[int] = None) -> None:
        return None

    def publish(self, channel: str, message: Any) -> int:
        return 0

    def subscribe(
        self, channels: list[str], callback: Callable[[str, bytes], None]
    ) -> None:
        pass
