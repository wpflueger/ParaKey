#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/shared/src"

echo "=== Setting up KeyMuse ==="

# Create virtualenvs if they don't exist (ignore errors if they do)
pyenv virtualenv 3.12.3 keymuse-backend 2>/dev/null || true
pyenv virtualenv 3.12.3 keymuse-client 2>/dev/null || true

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pyenv local keymuse-backend
pip install -q -r requirements.txt
cd ..

# Install client dependencies
echo "Installing client dependencies..."
cd client
pyenv local keymuse-client
pip install -q -r requirements.txt
cd ..

# Start backend in background
echo "Starting backend server..."
cd backend
python -m keymuse_backend.server &
BACKEND_PID=$!
cd ..

# Give backend time to start
sleep 2

# Start client
echo "Starting client app..."
cd client
python -m keymuse_client.app
CLIENT_EXIT=$?

# Cleanup
echo "Shutting down backend..."
kill "$BACKEND_PID" 2>/dev/null || true

exit $CLIENT_EXIT
