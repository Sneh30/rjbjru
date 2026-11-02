#!/usr/bin/env bash
# Build and exercise the full Docker stack. Every assertion is on the running
# containers, not on a local dev server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API="http://127.0.0.1:8000"
WEB="http://127.0.0.1:8080"
KEEP="${KEEP:-0}"

compose() {
  docker compose "$@"
}

cleanup() {
  if [[ "$KEEP" != "1" ]]; then
    compose down --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

json_field() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

path, field = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as handle:
    value = json.load(handle)
for part in field.split("."):
    value = value[part]
print(value)
PY
}

wait_for() {
  local url="$1" label="$2" deadline=$((SECONDS + 120))
  while (( SECONDS < deadline )); do
    if curl -fsS -o /dev/null "$url"; then
      echo "ok: $label"
      return 0
    fi
    sleep 2
  done
  echo "error: timed out waiting for $label at $url" >&2
  compose logs --tail=80 api web >&2 || true
  return 1
}

assert_contains() {
  local haystack="$1" needle="$2" label="$3"
  if [[ "$haystack" != *"$needle"* ]]; then
    echo "error: $label did not contain '$needle'" >&2
    exit 1
  fi
  echo "ok: $label"
}

assert_header() {
  local headers="$1" name="$2" label="$3"
  if ! grep -qi "^$name:" <<<"$headers"; then
    echo "error: $label is missing header '$name'" >&2
    printf '%s\n' "$headers" >&2
    exit 1
  fi
  echo "ok: $label"
}

echo "== docker compose build =="
compose build

echo "== docker compose up =="
compose up -d

wait_for "$API/api/v1/health" "API health"
wait_for "$WEB/" "web root"
wait_for "$WEB/api/v1/health" "web -> API proxy"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/windlens-smoke.XXXXXX")"
trap 'rm -rf "$tmp"; cleanup' EXIT

curl -fsS "$API/api/v1/health" -o "$tmp/health.json"
curl -fsS "$API/api/v1/meta" -o "$tmp/meta.json"
curl -fsS "$WEB/api/v1/meta" -o "$tmp/meta-web.json"
curl -fsS "$API/api/v1/decision-view?delivery_date=2026-01-15&cutoff=09%3A00" -o "$tmp/decision.json"
curl -fsS "$WEB/api/v1/decision-view?delivery_date=2026-01-15&cutoff=09%3A00" -o "$tmp/decision-web.json"

[[ "$(json_field "$tmp/health.json" status)" == "ok" ]]
[[ "$(json_field "$tmp/health.json" data_fingerprint)" == "$(json_field "$tmp/meta.json" data.fingerprint)" ]]
[[ "$(json_field "$tmp/meta.json" product)" == "WindLens" ]]
[[ "$(json_field "$tmp/decision.json" delivery_date)" == "2026-01-15" ]]
[[ "$(json_field "$tmp/decision.json" coverage.with_forecast)" -ge 24 ]]
echo "ok: API JSON fields and fingerprint"

cmp -s "$tmp/meta.json" "$tmp/meta-web.json"
cmp -s "$tmp/decision.json" "$tmp/decision-web.json"
echo "ok: nginx proxy payload matches direct API payload"

root_html="$(curl -fsS "$WEB/")"
assert_contains "$root_html" '<div id="root">' "SPA shell"
spa_html="$(curl -fsS "$WEB/desk?date=2026-01-15")"
assert_contains "$spa_html" '<div id="root">' "SPA history fallback"

headers="$(curl -fsS -D - -o /dev/null "$WEB/")"
assert_header "$headers" "content-security-policy" "static CSP header"
assert_header "$headers" "x-content-type-options" "static nosniff header"

api_headers="$(curl -fsS -D - -o /dev/null "$API/api/v1/meta")"
assert_header "$api_headers" "etag" "API ETag"
assert_header "$api_headers" "x-request-id" "API request id"

etag="$(curl -fsS -D - -o /dev/null "$API/api/v1/meta" | tr -d '\r' | awk -F': ' 'tolower($1)=="etag"{print $2}')"
status="$(curl -sS -o /dev/null -w '%{http_code}' -H "If-None-Match: $etag" "$API/api/v1/meta")"
[[ "$status" == "304" ]]
echo "ok: conditional request returns 304"

csv_headers="$(curl -fsS -D - -o /dev/null "$WEB/api/v1/export/decision-view.csv?delivery_date=2026-01-15&cutoff=09%3A00")"
assert_header "$csv_headers" "content-type" "CSV content type"
assert_contains "$(tr '[:upper:]' '[:lower:]' <<<"$csv_headers")" "text/csv" "CSV media type"
csv_body="$(curl -fsS "$WEB/api/v1/export/decision-view.csv?delivery_date=2026-01-15&cutoff=09%3A00")"
assert_contains "$csv_body" "delivery_date,cutoff_utc,start_time_utc" "CSV header row"

docs_status="$(curl -sS -o /dev/null -w '%{http_code}' "$API/api/docs")"
[[ "$docs_status" == "200" ]]
echo "ok: API docs return 200"

echo "== container state =="
compose ps

echo
echo "Docker smoke passed: API on :8000, web on :8080, health, proxy, SPA fallback, headers, ETag, CSV."
