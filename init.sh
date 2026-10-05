#!/bin/bash
set -euo pipefail

echo "=== Bootstrapping dev environment ==="

# Backend dependencies
cd backend && uv sync && cd ..

# Frontend dependencies
cd frontend && npm ci && cd ..

# Environment
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your API keys"
fi

# Local dev servers (backend + frontend via single npm start)
npm start > .dev-servers.log 2>&1 &

# Health checks
echo "Waiting for services..."
for url in http://localhost:8000/health http://localhost:5173; do
  for i in 1 2 3 4 5; do
    if curl -sf "$url" > /dev/null; then echo "OK $url"; break; fi
    [ "$i" -eq 5 ] && { echo "FAILED $url"; exit 1; }
    sleep 2
  done
done

echo "=== Environment ready ==="
