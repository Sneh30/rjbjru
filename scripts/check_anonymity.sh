#!/usr/bin/env bash
# Scan the repository text and commit metadata for identity leaks.
#
# The human may supply .anonymity-denylist (gitignored) with one literal string
# per line: real name, handle, email, employer, college. Until that file exists
# this script can still prove the generic checks (author fields, Docker labels,
# neutral git identity), but it cannot guess private identifiers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

failed=0
note() { echo "$*"; }
fail() { echo "FAIL: $*" >&2; failed=1; }

echo "== anonymity check =="

if [[ -f .anonymity-denylist ]]; then
  note "using .anonymity-denylist"
  while IFS= read -r token; do
    token="${token%$'\r'}"
    [[ -z "$token" || "${token:0:1}" == "#" ]] && continue
    if matches="$(git grep -I -n -F -- "$token" -- . 2>/dev/null)"; then
      fail "denylisted string found:"
      printf '%s\n' "$matches" >&2
    fi
  done < .anonymity-denylist
else
  note "WARN: .anonymity-denylist is absent; private identifiers were not checked."
  note "      The human must add it before the public push (H2)."
fi

if [[ -f frontend/package.json ]] && grep -nE '"author"|"contributors"|"maintainers"' frontend/package.json; then
  fail "frontend/package.json declares an author/contributor field"
fi

if grep -RInE '^\s*(authors|maintainers)\s*=' backend/pyproject.toml 2>/dev/null; then
  fail "backend/pyproject.toml declares authorship metadata"
fi

if git grep -InE 'LABEL[[:space:]]+maintainer' -- '*Dockerfile*' '*.dockerfile' 2>/dev/null; then
  fail "a Dockerfile has a maintainer label"
fi

name="$(git config --local user.name || true)"
email="$(git config --local user.email || true)"
if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
  note "note: local git identity check skipped in CI; commit authors are checked below"
elif [[ "$name" != "dev" || "$email" != "dev@users.noreply.invalid" ]]; then
  fail "local git identity is not the neutral 'dev <dev@users.noreply.invalid>' identity (name='$name', email='$email')"
else
  note "ok: local git identity is neutral"
fi

if git rev-parse --verify HEAD >/dev/null 2>&1; then
  while IFS= read -r author; do
    [[ -z "$author" ]] && continue
    if [[ "$author" != "dev <dev@users.noreply.invalid>" ]]; then
      fail "commit author is not neutral: $author"
    fi
  done < <(git log --format='%an <%ae>' | sort -u)
  note "ok: commit authors are neutral"
else
  note "note: no commits yet; commit author check skipped"
fi

if (( failed )); then
  echo "anonymity check FAILED" >&2
  exit 1
fi

echo "anonymity check passed (denylist, tracked text and commit authors)"
