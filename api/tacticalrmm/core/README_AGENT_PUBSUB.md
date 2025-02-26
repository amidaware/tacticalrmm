# Agent Updates Redis Pub/Sub

This document explains the Redis pub/sub implementation for synchronizing NATS configuration across microservices in Tactical RMM.

## Overview

When agents are registered or updated in the system, the NATS configuration needs to be updated on all running instances of the application. This is managed through the `reload_nats()` function, which:

1. Rebuilds the NATS configuration with updated agent information
2. Writes the configuration to disk
3. Sends a signal to the NATS server to reload
4. Publishes a notification to other microservices to do the same

## How It Works

1. When `reload_nats()` is called in one microservice (typically during agent registration or updates), it:
   - Rebuilds the NATS configuration by gathering agent information
   - Writes the configuration to the file `nats-rmm.conf`
   - Signals the NATS server to reload
   - Publishes a notification to the `agent_updates` Redis channel with a unique source ID

2. All other microservices subscribe to the `agent_updates` channel
   - When a notification is received, they call their own `reload_nats(publish=False)` function
   - The `publish=False` parameter prevents an infinite loop of notifications
   - Each microservice ignores notifications that originated from itself using the source ID

## Implementation

The implementation consists of just a few straightforward components:

### 1. Direct Redis Access

We use the `redis-py` library directly to handle pub/sub functionality:

```python
import redis
import os

def get_redis_client():
    """Get a Redis client using the REDIS_HOST environment variable."""
    # Get Redis host from environment variable
    redis_host = os.environ.get('REDIS_HOST', '127.0.0.1')
    
    # Use default Redis port
    redis_port = 6379
    
    # Create and return Redis client
    return redis.Redis(host=redis_host, port=redis_port, db=0)
```

### 2. Publisher in reload_nats()

The `reload_nats()` function (in `tacticalrmm/utils.py`) publishes a notification when it's called:

```python
def reload_nats(*, publish: bool = True) -> None:
    # ... existing code to rebuild NATS config ...
    
    # Publish notification if requested
    if publish:
        try:
            from core.agent_updater import get_service_id, get_redis_client
            
            notification = {
                "type": "nats_config_update",
                "timestamp": time.time(),
                "source_id": get_service_id(),  # Include source ID to prevent loops
                "agent_count": len(agent_ids)
            }
            
            # Publish to Redis directly
            redis_client = get_redis_client()
            result = redis_client.publish("agent_updates", json.dumps(notification))
            
        except Exception as e:
            logger.error(f"Failed to publish NATS update notification: {str(e)}")
```

### 3. Simple Subscriber

The subscriber in `core/agent_updater.py` simply calls `reload_nats()` when it receives a notification:

```python
def start_listener(daemon: bool = True) -> threading.Thread:
    def listener_thread():
        while True:
            try:
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
```

## Usage

### Starting the Listener

The listener is started automatically when the application starts, or you can start it manually:

```bash
python manage.py start_agent_listener
```

## Benefits

This simple pub/sub system provides several benefits:

1. **Real-time Updates**: All microservices update their NATS configuration immediately
2. **Automatic Synchronization**: No manual intervention needed to keep configurations in sync
3. **Lightweight**: Minimal overhead as we're just publishing a small notification
4. **Loop Prevention**: Service IDs prevent infinite notification loops

## Troubleshooting

If you're experiencing issues:

1. Check Redis is running: `redis-cli ping` should return `PONG`
2. Verify the subscriber is running: `ps aux | grep agent_listener`
3. Test the process manually:
   ```
   # In service 1
   python manage.py shell
   >>> from tacticalrmm.utils import reload_nats
   >>> reload_nats()
   
   # In service 2 (should automatically update in response)
   ```
4. Check the logs for errors 