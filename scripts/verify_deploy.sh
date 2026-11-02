#!/usr/bin/env bash
# Verify a public WindLens deployment without assuming which host it runs on.
# Usage: bash scripts/verify_deploy.sh https://your-project.vercel.app
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <base-url>" >&2
  exit 2
fi

BASE="${1%/}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/windlens-deploy.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

check_status() {
  local path="$1" expected="${2:-200}"
  local code
  code="$(curl -sS -o "$TMP/body" -D "$TMP/headers" -w '%{http_code}' "$BASE$path" || true)"
  [[ "$code" == "$expected" ]] || {
    echo "--- headers for $path ---" >&2
    cat "$TMP/headers" >&2 || true
    fail "$path returned HTTP $code, expected $expected"
  }
  if [[ "$path" != /assets/* ]]; then
    if grep -qi '^x-vercel-protection:' "$TMP/headers"; then
      fail "$path is behind Vercel Deployment Protection (x-vercel-protection present)"
    fi
  fi
  echo "ok: $path -> $code"
}

json_check() {
  local file="$1" expression="$2" label="$3"
  python3 - "$file" "$expression" "$label" <<'PY'
import json
import sys

path, expression, label = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)
value = data
for part in expression.split("."):
    if isinstance(value, list):
        value = value[int(part)]
    else:
        value = value[part]
if value is None or value == "" or value == [] or value == {}:
    raise SystemExit(f"FAIL: {label} resolved to an empty value")
print(f"ok: {label} = {value!r}")
PY
}

echo "== WindLens deployment verification =="
echo "base: $BASE"

check_status "/"
check_status "/desk"
check_status "/revisions"
check_status "/api/v1/health"
check_status "/api/v1/meta"
check_status "/api/v1/decision-view?delivery_date=2026-01-15&cutoff=09%3A00"
check_status "/api/v1/accuracy/summary?start=2026-01-02&end=2026-02-01&cutoff=09%3A00"
check_status "/api/docs"
check_status "/api/static/swagger/swagger-ui.css"
check_status "/api/static/swagger/swagger-ui-bundle.js"
check_status "/api/openapi.json"

curl -fsS "$BASE/api/v1/health" -o "$TMP/health.json"
curl -fsS "$BASE/api/v1/meta" -o "$TMP/meta.json"
curl -fsS "$BASE/api/v1/decision-view?delivery_date=2026-01-15&cutoff=09%3A00" -o "$TMP/decision.json"
curl -fsS "$BASE/api/v1/accuracy/summary?start=2026-01-02&end=2026-02-01&cutoff=09%3A00" -o "$TMP/summary.json"

json_check "$TMP/health.json" status "health status"
json_check "$TMP/health.json" data_fingerprint "snapshot fingerprint"
json_check "$TMP/meta.json" product "product name"
json_check "$TMP/meta.json" data.fingerprint "manifest fingerprint"
json_check "$TMP/decision.json" coverage.with_forecast "decision coverage"
json_check "$TMP/summary.json" metrics.n "scored hours"

python3 - "$TMP/health.json" "$TMP/meta.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    health = json.load(handle)
with open(sys.argv[2], encoding="utf-8") as handle:
    meta = json.load(handle)
if health["data_fingerprint"] != meta["data"]["fingerprint"]:
    raise SystemExit("FAIL: health and meta fingerprints disagree")
print("ok: health and meta refer to the same snapshot")
PY

headers="$(curl -fsS -D - -o /dev/null "$BASE/")"
for expected in "x-content-type-options: nosniff" "content-security-policy:"; do
  if ! grep -qi "$expected" <<<"$headers"; then
    fail "missing security header: $expected"
  fi
done
echo "ok: static security headers present"

html="$(curl -fsS "$BASE/desk")"
grep -q '<div id="root">' <<<"$html" || fail "/desk did not return the SPA shell"
echo "ok: SPA history fallback serves the app"

# Lighthouse audits these two paths directly. They must be real static files,
# not the SPA shell with a 200 status.
robots_code="$(curl -sS -o "$TMP/robots.txt" -D "$TMP/robots.headers" -w '%{http_code}' "$BASE/robots.txt" || true)"
[[ "$robots_code" == "200" ]] || fail "/robots.txt returned HTTP $robots_code, expected 200"
grep -qi '^content-type: text/plain' "$TMP/robots.headers" || fail "/robots.txt is not served as text/plain"
grep -q '^User-agent: \*' "$TMP/robots.txt" || fail "/robots.txt does not contain a User-agent directive"
if grep -q '<div id="root">' "$TMP/robots.txt"; then
  fail "/robots.txt fell through to the SPA shell"
fi

favicon_code="$(curl -sS -o "$TMP/favicon.ico" -D "$TMP/favicon.headers" -w '%{http_code}' "$BASE/favicon.ico" || true)"
[[ "$favicon_code" == "200" ]] || fail "/favicon.ico returned HTTP $favicon_code, expected 200"
grep -qi '^content-type: image/' "$TMP/favicon.headers" || fail "/favicon.ico is not served as an image"
python3 - "$TMP/favicon.ico" <<'PY'
import sys

with open(sys.argv[1], "rb") as handle:
    header = handle.read(4)
if header != b"\x00\x00\x01\x00":
    raise SystemExit("FAIL: /favicon.ico is not a valid ICO file")
print("ok: favicon.ico is a valid ICO file")
PY
echo "ok: robots.txt and favicon.ico are real static files"

docs_html="$(curl -fsS "$BASE/api/docs")"
grep -q '/api/static/swagger/swagger-ui-bundle.js' <<<"$docs_html" || fail "docs UI is not self-hosted"
if grep -q 'cdn.jsdelivr.net' <<<"$docs_html"; then
  fail "docs UI still depends on a CDN"
fi
echo "ok: docs UI assets are self-hosted"

csv_headers="$(curl -fsS -D - -o /dev/null "$BASE/api/v1/export/decision-view.csv?delivery_date=2026-01-15&cutoff=09%3A00")"
grep -qi 'content-type: text/csv' <<<"$csv_headers" || fail "CSV export has the wrong content type"
echo "ok: CSV export"

echo
echo "Deployment verification passed for $BASE"
