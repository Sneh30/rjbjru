#!/usr/bin/env bash
# Fail unless the public documentation contains one coherent set of real URLs.
# Run after scripts/set_public_urls.sh and before publishing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
from pathlib import Path
import re
import sys

docs = [
    Path("README.md"),
    Path("docs/FORM_ANSWERS.md"),
    Path("docs/AUDIT.md"),
    Path("HUMAN_ACTIONS.md"),
]
required = [Path("README.md"), Path("docs/FORM_ANSWERS.md")]

problems = []
for path in docs:
    if not path.exists():
        problems.append(f"missing {path}")
        continue
    text = path.read_text()
    for marker in ("__GITHUB_OWNER__", "__VERCEL_HOST__"):
        if marker in text:
            problems.append(f"{path} still contains {marker}")

repo_pattern = re.compile(r"https://github\.com/([A-Za-z0-9-]+)/rjbjru\b")
host_pattern = re.compile(r"https://([a-z0-9-]+\.vercel\.app)\b")

owners = set()
hosts = set()
for path in docs:
    if not path.exists():
        continue
    text = path.read_text()
    owners.update(repo_pattern.findall(text))
    hosts.update(host_pattern.findall(text))

for path in required:
    if not path.exists():
        continue
    text = path.read_text()
    if not repo_pattern.search(text):
        problems.append(f"{path} has no https://github.com/<owner>/rjbjru URL")
    if not host_pattern.search(text):
        problems.append(f"{path} has no https://<project>.vercel.app URL")

if len(owners) != 1:
    problems.append(f"expected exactly one GitHub owner, found {sorted(owners) or 'none'}")
if len(hosts) != 1:
    problems.append(f"expected exactly one Vercel host, found {sorted(hosts) or 'none'}")

if problems:
    for problem in problems:
        print(f"FAIL: {problem}", file=sys.stderr)
    raise SystemExit(1)

print(f"ok: GitHub owner = {next(iter(owners))}")
print(f"ok: Vercel host = {next(iter(hosts))}")
print("public URL check passed")
PY
