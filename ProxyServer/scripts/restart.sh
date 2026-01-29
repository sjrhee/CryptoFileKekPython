#!/bin/bash

cd "$(dirname "$0")"

echo "Restarting ProxyServer..."

./stop.sh

# Wait for a moment to ensure ports are released
sleep 2

./start.sh
