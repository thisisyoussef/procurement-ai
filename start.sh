#!/bin/bash
# Start both backend and frontend for Tamkin
# Usage: ./start.sh

set -e

echo "Starting Tamkin..."
echo ""

# Check if port 8000 is already in use
if lsof -i :8000 >/dev/null 2>&1; then
    echo "Port 8000 already in use. Kill existing process? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        kill $(lsof -t -i :8000) 2>/dev/null || true
        sleep 1
    fi
fi

# Start backend
echo "[1/2] Starting FastAPI backend on http://localhost:8000 ..."
cd "$(dirname "$0")"
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to be ready
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  Backend is healthy!"
        break
    fi
    sleep 1
done

# Start frontend
echo "[2/2] Starting Next.js frontend on http://localhost:3000 ..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "Both servers are running!"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Trap Ctrl+C to kill both processes
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# Wait for either to exit
wait
