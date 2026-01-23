#!/bin/bash
echo "Restarting application..."
./stop.sh
sleep 2
./start.sh
