#!/bin/bash

# Ensure we are in ProxyServer directory
cd "$(dirname "$0")/.."

# Source venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Python App
echo "Starting Python App..."
nohup python3 src/app.py > app.log 2>&1 &
echo $! > app.pid

# Start Nginx
echo "Starting Nginx..."
# We need to ensure logs directory exists for nginx default logs if valid
mkdir -p logs
# Nginx requires absolute path for config usually, or relative to prefix. 
# We set prefix to current dir via -p.
# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Nginx could not be found. Please install nginx."
    exit 1
fi

# Run Nginx in background for this simple script
# Note: nginx.conf has 'daemon off', so we background it here.
nohup nginx -p $(pwd) -c nginx.conf > nginx.log 2>&1 &
echo $! > nginx.pid

echo "ProxyServer started."
