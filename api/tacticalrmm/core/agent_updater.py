"""
Agent update notification subscriber.

This module provides functionality to listen for NATS configuration update
notifications via Redis pub/sub and reload the NATS configuration accordingly.
"""

import json
import logging
import os
import threading
import time
import uuid

import redis

logger = logging.getLogger(__name__)

# Generate a unique ID for this service instance to prevent notification loops
_SERVICE_ID = str(uuid.uuid4())


def get_service_id() -> str:
    """Return the unique ID for this service instance."""
    return _SERVICE_ID


def handle_agent_update(channel: str, message: bytes) -> None:
    """
    Handle agent update notifications from Redis pub/sub.

    When a notification is received, this function checks if it's a NATS
    configuration update notification and if it didn't originate from this
    service. If both conditions are met, it calls reload_nats() to update
    the NATS configuration locally.

    Args:
        channel: The Redis channel the message was received on
        message: The message payload as bytes
    """
    try:
        data = json.loads(message.decode("utf-8"))

        if data.get("type") == "nats_config_update":
            if data.get("source_id") == _SERVICE_ID:
                logger.debug("Ignoring NATS update from self (ID: %s)", _SERVICE_ID)
                return

            logger.info(
                "Received NATS configuration update notification for %s agents",
                data.get("agent_count"),
            )

            # Import here to avoid circular import
            from django.db import connection
            from tacticalrmm.utils import reload_nats

            # Close any existing database connection before accessing DB
            # This ensures we get a fresh connection for each message
            connection.close()

            try:
                # Don't publish again to avoid loops
                reload_nats(publish=False)
                logger.debug("Successfully reloaded NATS configuration")
            finally:
                # Always close connection after use to prevent leaks in thread
                connection.close()

    except Exception as e:
        logger.error("Error handling agent update: %s", e)


def get_redis_client():
    """Get a Redis client using the REDIS_HOST environment variable."""
    redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    logger.debug("Connecting to Redis at %s:%d", redis_host, redis_port)
    return redis.Redis(host=redis_host, port=redis_port, db=0)


def start_listener(daemon: bool = True) -> threading.Thread:
    """
    Start a Redis pub/sub listener in a background thread.

    Args:
        daemon: Whether to run the thread as a daemon

    Returns:
        The started thread object
    """

    def listener_thread():
        logger.info("Agent listener thread started (service_id=%s)", _SERVICE_ID)

        while True:
            try:
                logger.info("Starting Redis pub/sub listener for agent updates")

                redis_client = get_redis_client()
                pubsub = redis_client.pubsub()

                try:
                    redis_client.ping()
                    logger.debug("Redis ping OK")
                except Exception as ping_error:
                    logger.warning("Redis ping failed: %s", ping_error)

                pubsub.subscribe("agent_updates")
                logger.debug("Subscribed to 'agent_updates' channel")

                for message in pubsub.listen():
                    logger.debug("Received message type: %s", message["type"])
                    if message["type"] == "message":
                        handle_agent_update(message["channel"], message["data"])

            except Exception as e:
                logger.error("Redis subscription error: %s", e)
                time.sleep(10)

    thread = threading.Thread(target=listener_thread)
    thread.daemon = daemon
    thread.start()
    logger.info("Agent listener thread started (daemon=%s)", daemon)

    return thread
