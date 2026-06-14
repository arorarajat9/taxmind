#!/usr/bin/env bash
# Start the TaxMind API and frontend together for the full web demo.
set -e
cd "$(dirname "$0")/.."

PY=.venv/bin/python
[ -x "$PY" ] || { echo "Run 'make setup' first (no .venv found)."; exit 1; }

# ensure demo data exists
[ -f data/synthetic/purchase_register.xlsx ] || $PY scripts/generate_demo_data.py

echo "Starting API on http://localhost:8000 ..."
.venv/bin/uvicorn backend.api.main:app --port 8000 &
API_PID=$!
trap "echo; echo 'Stopping...'; kill $API_PID 2>/dev/null" EXIT INT TERM

# wait for API health
for i in $(seq 1 20); do
  curl -sf localhost:8000/api/health >/dev/null 2>&1 && break
  sleep 1
done
echo "API ready. Starting frontend on http://localhost:3000 ..."
cd frontend && npm run dev
