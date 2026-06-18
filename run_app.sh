#!/bin/bash

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "=== Shutting down servers ==="
    if [ -n "$PYTHON_PID" ]; then
        kill "$PYTHON_PID" 2>/dev/null || true
    fi
    if [ -n "$VITE_PID" ]; then
        kill "$VITE_PID" 2>/dev/null || true
    fi
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM to clean up background tasks
trap cleanup SIGINT SIGTERM EXIT

echo "=== Starting Audio File Server (Port 8080) ==="
python3 -m http.server 8080 > /dev/null 2>&1 &
PYTHON_PID=$!
echo "Audio server running under PID: $PYTHON_PID"

echo "=== Starting Review UI Dev Server (Port 5173) ==="
cd review-ui
npm run dev &
VITE_PID=$!
echo "Vite UI running under PID: $VITE_PID"

# Wait for both processes
wait "$VITE_PID"
