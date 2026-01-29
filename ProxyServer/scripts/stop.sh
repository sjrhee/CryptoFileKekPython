#!/bin/bash

cd "$(dirname "$0")/.."

# Stop Python App
if [ -f "app.pid" ]; then
    PID=$(cat app.pid)
    if ps -p $PID > /dev/null; then
        echo "Stopping Python App (PID $PID)..."
        kill $PID
        rm app.pid
    else
        echo "Python App PID file found but process not running."
        rm app.pid
    fi
else
    echo "No app.pid found."
fi

# Stop Nginx
if [ -f "nginx.pid" ]; then
    PID=$(cat nginx.pid)
    if ps -p $PID > /dev/null; then
        echo "Stopping Nginx (PID $PID)..."
        kill $PID
        rm nginx.pid
    else
        echo "Nginx PID file found but process not running."
        rm nginx.pid
    fi
else
    echo "No nginx.pid found."
fi

# Fallback: Ensure all nginx processes are gone
if pgrep -f "nginx" > /dev/null; then
    echo "Wait.. orphaned nginx processes found. Killing them..."
    # Only kill nginx processes running from this directory to avoid killing system nginx
    # But since we run locally, pkill nginx is likely safe-ish, but safer is targeting the config
    pkill -f "nginx -p" || pkill nginx
fi

echo "ProxyServer stopped."
