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
import sys

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
        # Force output to console for debugging
        print(f"RECEIVED MESSAGE: {message}", flush=True)
        
        data = json.loads(message.decode('utf-8'))
        
        if data.get('type') == 'nats_config_update':
            # Don't reload if this is the originating service
            if data.get('source_id') == _SERVICE_ID:
                print(f"Ignoring NATS update from self (ID: {_SERVICE_ID})", flush=True)
                logger.debug("Ignoring NATS update from self")
                return
                
            print(f"Received NATS configuration update notification for {data.get('agent_count')} agents", flush=True)
            logger.info(f"Received NATS configuration update notification for {data.get('agent_count')} agents")
            
            # Import here to avoid circular import
            from tacticalrmm.utils import reload_nats
            
            # Call reload_nats to update this service's configuration
            # Don't publish again to avoid loops
            print("Calling reload_nats(publish=False)...", flush=True)
            reload_nats(publish=False)
            print("Successfully reloaded NATS configuration", flush=True)
            
    except Exception as e:
        error_msg = f"Error handling agent update: {str(e)}"
        print(f"ERROR: {error_msg}", flush=True)
        logger.error(error_msg)

def get_redis_client():
    """Get a Redis client using the REDIS_HOST environment variable."""
    # Get Redis host from environment variable
    redis_host = os.environ.get('REDIS_HOST', '127.0.0.1')
    
    # Use default Redis port
    redis_port = 6379
    
    print(f"Connecting to Redis at {redis_host}:{redis_port}", flush=True)
    
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
        print("===== AGENT LISTENER THREAD STARTED =====", flush=True)
        print(f"Service ID: {_SERVICE_ID}", flush=True)
        
        while True:
            try:
                print("Starting Redis pub/sub listener for agent updates", flush=True)
                logger.info("Starting Redis pub/sub listener for agent updates")
                
                # Get Redis connection directly
                redis_client = get_redis_client()
                pubsub = redis_client.pubsub()
                
                # Test Redis connection
                try:
                    ping_result = redis_client.ping()
                    print(f"Redis ping result: {ping_result}", flush=True)
                except Exception as ping_error:
                    print(f"Redis ping failed: {str(ping_error)}", flush=True)
                
                print("Subscribing to 'agent_updates' channel...", flush=True)
                pubsub.subscribe('agent_updates')
                print("Successfully subscribed to 'agent_updates' channel", flush=True)
                
                # Process messages as they come in
                print("Entering message processing loop...", flush=True)
                for message in pubsub.listen():
                    print(f"Received message type: {message['type']}", flush=True)
                    if message['type'] == 'message':
                        handle_agent_update(message['channel'], message['data'])
                        
            except Exception as e:
                error_msg = f"Redis subscription error: {str(e)}"
                print(f"ERROR: {error_msg}", flush=True)
                logger.error(error_msg)
                print("Waiting 10 seconds before reconnecting...", flush=True)
                time.sleep(10)  # Wait before reconnecting
    
    print("Creating agent listener thread...", flush=True)
    thread = threading.Thread(target=listener_thread)
    thread.daemon = daemon
    print(f"Starting thread with daemon={daemon}...", flush=True)
    thread.start()
    print("Thread started successfully", flush=True)
    
    return thread

# Example usage in a Django management command:
# def handle(self, *args, **options):
#     thread = start_listener(daemon=False)
#     try:
#         thread.join()
#     except KeyboardInterrupt:
#         pass 