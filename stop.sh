#!/bin/bash

if [ -f app.pid ]; then
    PID=$(cat app.pid)
    echo "Stopping CryptoFileKekPython (PID: $PID)..."
    kill $PID
    rm app.pid
    echo "Stopped."
else
    echo "app.pid not found. Attempting to find process by name..."
    if pkill -f "python app.py"; then
        echo "Stopped via pkill."
    else
        echo "No running process found."
    fi
fi
