#!/usr/bin/env bash
# Insert the fresh neutral account handles into the tracked documentation.
#
# Usage:
#   bash scripts/set_public_urls.sh --github-owner <owner>
#   bash scripts/set_public_urls.sh --vercel-host <project>.vercel.app
#   bash scripts/set_public_urls.sh --github-owner <owner> --vercel-host <host>
#
# The two values can be supplied in either order, on separate runs. The script
# refuses handles that contain a token from the private .anonymity-denylist.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat >&2 <<'EOF'
usage: bash scripts/set_public_urls.sh --github-owner <owner> [--vercel-host <host>]
       bash scripts/set_public_urls.sh --vercel-host <host> [--github-owner <owner>]
EOF
}

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

github_owner=""
vercel_host=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --github-owner)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      github_owner="$2"
      shift 2
      ;;
    --vercel-host)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      vercel_host="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$github_owner" || -n "$vercel_host" ]] || { usage; exit 2; }

reject_denylisted() {
  local candidate="$1" token
  [[ -f .anonymity-denylist ]] || return 0
  while IFS= read -r token; do
    token="${token%$'\r'}"
    [[ -z "$token" || "${token:0:1}" == "#" ]] && continue
    if grep -Fiq -- "$token" <<<"$candidate"; then
      fail "value contains a denylisted identifier: $candidate"
    fi
  done < .anonymity-denylist
}

if [[ -n "$github_owner" ]]; then
  [[ "$github_owner" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,37}[A-Za-z0-9])?$ ]] || fail "invalid GitHub owner: $github_owner"
  reject_denylisted "$github_owner"
fi

if [[ -n "$vercel_host" ]]; then
  vercel_host="${vercel_host#https://}"
  vercel_host="${vercel_host#http://}"
  vercel_host="${vercel_host%%/*}"
  [[ "$vercel_host" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.vercel\.app$ ]] || fail "invalid Vercel host: $vercel_host"
  reject_denylisted "$vercel_host"
fi

python3 - "$github_owner" "$vercel_host" <<'PY'
from pathlib import Path
import sys

owner, host = sys.argv[1], sys.argv[2]
files = [
    Path("README.md"),
    Path("docs/FORM_ANSWERS.md"),
    Path("docs/AUDIT.md"),
    Path("docs/VIDEO_SCRIPT.md"),
    Path("HUMAN_ACTIONS.md"),
]
replacements = {}
if owner:
    replacements["__GITHUB_OWNER__"] = owner
if host:
    replacements["__VERCEL_HOST__"] = host

changed = []
for path in files:
    if not path.exists():
        continue
    text = path.read_text()
    updated = text
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    if updated != text:
        path.write_text(updated)
        changed.append(str(path))

print("updated:", ", ".join(changed) if changed else "nothing")

decision = Path(".anonymity-decision")
if decision.exists():
    text = decision.read_text()
    lines = []
    for line in text.splitlines():
        if line.startswith("- GitHub owner:") or line.startswith("- Vercel host:"):
            continue
        lines.append(line)
    if owner:
        lines.append(f"- GitHub owner: {owner}")
    if host:
        lines.append(f"- Vercel host: {host}")
    decision.write_text("\n".join(lines).rstrip() + "\n")
    print("updated: .anonymity-decision")
PY

if [[ -n "$github_owner" ]]; then
  echo "GitHub owner: $github_owner"
fi
if [[ -n "$vercel_host" ]]; then
  echo "Vercel host: $vercel_host"
fi
echo "next: review git diff, run bash scripts/check_anonymity.sh, then scripts/check_public_urls.sh"
