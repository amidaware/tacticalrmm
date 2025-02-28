#!/bin/bash

# Exit on any error
set -e

# Set PYTHONUNBUFFERED to disable output buffering
export PYTHONUNBUFFERED=1

# Print header with timestamp
echo "===================================="
echo "Starting agent listener at $(date)"
echo "Current directory: $(pwd)"
echo "PATH: $PATH"
echo "TACTICAL_DIR: $TACTICAL_DIR"
echo "REDIS_HOST: $REDIS_HOST"
echo "===================================="

# Make sure we're in the right directory
cd ${TACTICAL_DIR}/api

# Python path information
which python || echo "Python not found in PATH"
which python3 || echo "Python3 not found in PATH"

# Try to use the virtual environment if it exists
if [ -f "${TACTICAL_DIR}/api/env/bin/activate" ]; then
    echo "Activating virtual environment at ${TACTICAL_DIR}/api/env/bin/activate"
    source ${TACTICAL_DIR}/api/env/bin/activate
fi

# More debugging info
echo "Using Python: $(which python)"
python --version

# Run the agent listener in foreground mode
echo "Starting agent listener..."
python manage.py start_agent_listener --foreground

# This should never be reached due to the foreground mode
echo "Agent listener exited unexpectedly at $(date)"
exit 1
