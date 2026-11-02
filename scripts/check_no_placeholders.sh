#!/usr/bin/env bash
# Fail on unresolved authoring markers in deliverable, tracked text files.
#
# The six supplied specification documents are inputs, not deliverables, and
# intentionally contain meta-instructions such as an unresolved placeholder used
# to describe a requirement. They are excluded explicitly and the exclusion is
# recorded in docs/AUDIT.md. Generated and third-party files are excluded too:
# their contents are not authored here.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EXCLUDES=(
  ':(exclude)docs/MASTER_PROMPT.md'
  ':(exclude)docs/PRD.md'
  ':(exclude)docs/SAS.md'
  ':(exclude)docs/IMPLEMENTATION.md'
  ':(exclude)docs/VERIFICATION_GATE.md'
  ':(exclude)docs/ENGINEERING_REFERENCE.md'
  ':(exclude)docs/AGENT_CAPABILITIES.md'
  ':(exclude)frontend/package-lock.json'
  ':(exclude)frontend/src/types/openapi.d.ts'
  # Vendored third-party Swagger UI assets; upstream text is not authored here.
  ':(exclude)backend/app/static/swagger/**'
  # The checker source necessarily contains the markers it searches for.
  ':(exclude)scripts/check_no_placeholders.sh'
)

echo "== placeholder check =="
echo "scanning tracked deliverable text files"

# Case-sensitive on purpose: a legitimate word such as "todo" in prose is not a
# marker, while the conventional markers are upper-case.
if matches="$(git grep -InE 'TODO|FIXME|\bXXX\b|lorem ipsum|<<[A-Z][A-Z0-9_]*>>' -- . "${EXCLUDES[@]}" 2>/dev/null)"; then
  echo "FAIL: unresolved authoring markers found:" >&2
  printf '%s\n' "$matches" >&2
  exit 1
fi

echo "ok: no unresolved authoring markers, lorem ipsum or <<TOKENS>> in deliverables"
