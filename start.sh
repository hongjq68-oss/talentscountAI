#!/usr/bin/env bash
# One-command local run: builds the UI and serves UI + API on http://localhost:8000
set -e
cd "$(dirname "$0")"
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt
(cd frontend && npm install --silent && npm run build --silent)
cd backend && exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
