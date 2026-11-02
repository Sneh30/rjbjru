#!/usr/bin/env bash
# Trace every numeric claim in the README, video script and form answers to
# docs/INSIGHTS.md. Fails on an exact-value mismatch; no silent rounding.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec python3 scripts/check_numbers_consistency.py
