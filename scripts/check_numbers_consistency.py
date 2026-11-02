#!/usr/bin/env python3
"""Trace every numeric claim in the README, video script and form answers.

The canonical source is ``docs/INSIGHTS.md``. A claim passes only when the same
numeric value appears in that file. No silent rounding is applied: a document
that says ``2,039 MW`` when the insight says ``2,038.9 MW`` fails and must be
fixed. Dates and clock times are removed before tokenising so a calendar day
cannot accidentally satisfy a metric claim.

Compared sections:
  * README.md — the ``Key findings`` section only (as required by the gate)
  * docs/VIDEO_SCRIPT.md — every blockquote narration line
  * docs/FORM_ANSWERS.md — the whole draft, because the form is pasted from it

Usage: python3 scripts/check_numbers_consistency.py
Exit status: 0 when every claim traces, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSIGHTS = ROOT / "docs" / "INSIGHTS.md"
README = ROOT / "README.md"
VIDEO = ROOT / "docs" / "VIDEO_SCRIPT.md"
FORM = ROOT / "docs" / "FORM_ANSWERS.md"

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
NUMBER_RE = re.compile(r"(?<![\w.])([+-]?\d[\d,]*(?:\.\d+)?)(?![\w])")


def strip_noise(text: str) -> str:
    """Remove dates and clock times so they cannot satisfy metric claims."""
    text = DATE_RE.sub(" ", text)
    return TIME_RE.sub(" ", text)


def numbers_in(text: str) -> set[Decimal]:
    """Return the set of numeric values present in a block of text."""
    values: set[Decimal] = set()
    for match in NUMBER_RE.finditer(strip_noise(text)):
        token = match.group(1).replace(",", "").lstrip("+")
        try:
            values.add(Decimal(token))
        except InvalidOperation:
            continue
    return values


def claims_in_lines(lines: list[tuple[int, str]]) -> list[tuple[int, Decimal, str]]:
    """Extract numeric claims with their source line numbers and context."""
    claims: list[tuple[int, Decimal, str]] = []
    for line_number, line in lines:
        cleaned = strip_noise(line)
        for match in NUMBER_RE.finditer(cleaned):
            token = match.group(1).replace(",", "").lstrip("+")
            try:
                value = Decimal(token)
            except InvalidOperation:
                continue
            claims.append((line_number, value, line.strip()))
    return claims


def readme_key_findings() -> list[tuple[int, str]]:
    """Return the README Key findings section, excluding its heading."""
    lines = README.read_text(encoding="utf-8").splitlines()
    start: int | None = None
    collected: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        if start is None:
            if line.strip() == "## Key findings":
                start = index
            continue
        if line.startswith("## "):
            break
        collected.append((index, line))
    if start is None:
        raise SystemExit("could not find '## Key findings' in README.md")
    return collected


def video_narration() -> list[tuple[int, str]]:
    """Return blockquote narration lines, which are the spoken script."""
    lines = VIDEO.read_text(encoding="utf-8").splitlines()
    collected: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(">"):
            collected.append((index, stripped.lstrip(">").strip()))
    return collected


def form_lines() -> list[tuple[int, str]]:
    """Return all form-answer lines; the whole draft is pasted by the human."""
    lines = FORM.read_text(encoding="utf-8").splitlines()
    return [(index, line) for index, line in enumerate(lines, start=1)]


def check(label: str, lines: list[tuple[int, str]], canonical: set[Decimal]) -> list[str]:
    """Check one document section and print every claim, traced or not."""
    claims = claims_in_lines(lines)
    failures: list[str] = []
    print(f"\n== {label}: {len(claims)} numeric claims ==")
    for line_number, value, context in claims:
        shown = f"{value.normalize():f}" if value == value.to_integral() else str(value)
        if value in canonical:
            status = "ok"
        else:
            status = "MISSING"
            failures.append(f"{label}:{line_number}: {shown} :: {context}")
        print(f"  {status:7} {shown:>12}  {label}:{line_number}  {context[:110]}")
    return failures


def main() -> int:
    canonical = numbers_in(INSIGHTS.read_text(encoding="utf-8"))
    print(f"canonical source: {INSIGHTS.relative_to(ROOT)} ({len(canonical)} distinct values)")

    failures: list[str] = []
    failures.extend(check("README Key findings", readme_key_findings(), canonical))
    failures.extend(check("VIDEO narration", video_narration(), canonical))
    failures.extend(check("FORM answers", form_lines(), canonical))

    total = sum(
        len(claims_in_lines(lines))
        for lines in (readme_key_findings(), video_narration(), form_lines())
    )
    print(f"\nchecked {total} claims against {len(canonical)} canonical values")
    if failures:
        print(f"\nFAIL: {len(failures)} claim(s) do not trace to docs/INSIGHTS.md", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("ok: every numeric claim traces exactly to docs/INSIGHTS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
