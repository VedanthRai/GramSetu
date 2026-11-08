#!/usr/bin/env bash
# Build the frontend and start GramSetu on http://127.0.0.1:8000 (macOS / Linux / Git Bash).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${GRAMSETU_PYTHON:-python3}"
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; fi
if [ -f "$ROOT/.venv/Scripts/python.exe" ]; then PY="$ROOT/.venv/Scripts/python.exe"; fi
(cd frontend && npm install --silent && npm run build --silent)
cd backend && exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
