#!/bin/bash
./stop.sh
echo "Waiting for port to release..."
sleep 2
./start.sh
