#!/usr/bin/env bash
# Regenerate the TypeScript contract from the live FastAPI OpenAPI schema.
# The generated file is committed, so CI can prove the client contract has not
# drifted from the server without importing any Python package.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-$ROOT/backend/.venv/bin/python}"

if [[ "$PY" == */* && ! -x "$PY" ]]; then
  echo "error: $PY not found; run 'make setup' first or set PYTHON=python" >&2
  exit 1
fi
if ! command -v "$PY" >/dev/null 2>&1 && [[ ! -x "$PY" ]]; then
  echo "error: Python interpreter '$PY' is not available" >&2
  exit 1
fi

tmp="$(mktemp "${TMPDIR:-/tmp}/windlens-openapi.XXXXXX.json")"
trap 'rm -f "$tmp"' EXIT

(
  cd "$ROOT/backend"
  "$PY" - "$tmp" <<'PY'
import json
import sys
from pathlib import Path

from app.main import app

target = Path(sys.argv[1])
schema = app.openapi()
target.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
)

(
  cd "$ROOT/frontend"
  npx --no-install openapi-typescript "$tmp" --output src/types/openapi.d.ts
)

echo "generated frontend/src/types/openapi.d.ts from app.openapi()"
