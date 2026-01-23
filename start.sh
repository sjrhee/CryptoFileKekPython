#!/bin/bash
# Load .env variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Starting CryptoFileKekPython..."
nohup python app.py > app.log 2>&1 &
echo $! > app.pid
echo "Application started. PID: $(cat app.pid). Logs: app.log"
