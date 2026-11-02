#!/usr/bin/env bash
# Fail unless the public documentation contains one coherent set of real URLs.
# This is the final public-link gate; it is safe to run before every push.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
from pathlib import Path
import re
import sys

owner = "Sneh30"
host = "windlens-vhdegk.vercel.app"
repo_url = f"https://github.com/{owner}/rjbjru"
host_url = f"https://{host}"

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
    if repo_url not in text:
        problems.append(f"{path} is missing {repo_url}")
    if host_url not in text:
        problems.append(f"{path} is missing {host_url}")

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

if owners != {owner}:
    problems.append(f"expected GitHub owner {owner!r}, found {sorted(owners) or 'none'}")
if hosts != {host}:
    problems.append(f"expected Vercel host {host!r}, found {sorted(hosts) or 'none'}")

if problems:
    for problem in problems:
        print(f"FAIL: {problem}", file=sys.stderr)
    raise SystemExit(1)

print(f"ok: GitHub owner = {owner}")
print(f"ok: Vercel host = {host}")
print("public URL check passed")
PY
