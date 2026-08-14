#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Railway start script — runs FastAPI (port 8000) and Streamlit (port $PORT)
# as a single service.
# ─────────────────────────────────────────────────────────────────────────────

set -e

# Use Railway's PORT env for Streamlit; default to 8501 locally
STREAMLIT_PORT="${PORT:-8501}"
BACKEND_PORT=8000

echo "▶ Starting FastAPI backend on port $BACKEND_PORT..."
uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port "$BACKEND_PORT" \
  --workers 1 &

# Give FastAPI a moment to start before Streamlit tries to call it
sleep 3

echo "▶ Starting Streamlit frontend on port $STREAMLIT_PORT..."
BACKEND_URL="http://localhost:$BACKEND_PORT" \
streamlit run frontend/app.py \
  --server.port "$STREAMLIT_PORT" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false

# If Streamlit exits, kill the background FastAPI process too
kill 0
