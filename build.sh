#!/bin/bash
# Build script for CryptoFileKekPython
# Sets up virtual environment and installs dependencies

echo "Building CryptoFileKekPython..."

# 1. Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "Build complete. Run ./start.sh to start the application."
