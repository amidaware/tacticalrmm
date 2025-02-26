"""
Agent update notification subscriber.

This module provides functionality to listen for NATS configuration update
notifications via Redis pub/sub and reload the NATS configuration accordingly.
"""

import json
import logging
import threading
import time
import uuid
import redis
import os

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
        data = json.loads(message.decode('utf-8'))
        
        if data.get('type') == 'nats_config_update':
            # Don't reload if this is the originating service
            if data.get('source_id') == _SERVICE_ID:
                logger.debug("Ignoring NATS update from self")
                return
                
            logger.info(f"Received NATS configuration update notification for {data.get('agent_count')} agents")
            
            # Import here to avoid circular import
            from tacticalrmm.utils import reload_nats
            
            # Call reload_nats to update this service's configuration
            # Don't publish again to avoid loops
            reload_nats(publish=False)
            
    except Exception as e:
        logger.error(f"Error handling agent update: {str(e)}")

def get_redis_client():
    """Get a Redis client using the REDIS_HOST environment variable."""
    # Get Redis host from environment variable
    redis_host = os.environ.get('REDIS_HOST', '127.0.0.1')
    
    # Use default Redis port
    redis_port = 6379
    
    # Create and return Redis client
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
        while True:
            try:
                logger.info("Starting Redis pub/sub listener for agent updates")
                
                # Get Redis connection directly
                redis_client = get_redis_client()
                pubsub = redis_client.pubsub()
                pubsub.subscribe('agent_updates')
                
                # Process messages as they come in
                for message in pubsub.listen():
                    if message['type'] == 'message':
                        handle_agent_update(message['channel'], message['data'])
                        
            except Exception as e:
                logger.error(f"Redis subscription error: {str(e)}")
                time.sleep(10)  # Wait before reconnecting
    
    thread = threading.Thread(target=listener_thread)
    thread.daemon = daemon
    thread.start()
    
    return thread

# Example usage in a Django management command:
# def handle(self, *args, **options):
#     thread = start_listener(daemon=False)
#     try:
#         thread.join()
#     except KeyboardInterrupt:
#         pass 