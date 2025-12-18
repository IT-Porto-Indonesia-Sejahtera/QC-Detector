#!/bin/bash
# Kill any existing processes on ports 8000 (backend) and 5173 (frontend)
lsof -t -i:8000 | xargs kill -9 2>/dev/null
lsof -t -i:5173 | xargs kill -9 2>/dev/null

echo "Starting Backend..."
# Assuming python3 is available (standard on macOS)
python3 prototype/backend/main.py &
BACKEND_PID=$!

echo "Starting Frontend..."
cd prototype/frontend
npm run dev -- --host &
FRONTEND_PID=$!

echo "Prototype running!"
echo "Backend: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
