#!/usr/bin/env python3
"""Estimate the spoken duration of docs/VIDEO_SCRIPT.md from its word count.

Each script section starts with a marker such as::

    <!-- section: S1 budget=25 title="Problem and promise" -->

The spoken narration is the blockquote text (`> ...`) in that section. The
checker counts words, estimates duration at 130 and 150 words per minute, and
fails when a section runs more than 10% over its spoken budget or when the total
at 130 wpm exceeds the 9:30 target. Screen directions and tables are not spoken.

Usage: python3 scripts/check_video_timing.py [path]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SCRIPT = Path(__file__).resolve().parents[1] / "docs" / "VIDEO_SCRIPT.md"
MARKER_RE = re.compile(
    r"<!--\s*section:\s*(?P<id>[A-Za-z0-9]+)\s+budget=(?P<budget>\d+)\s+"
    r'title="(?P<title>[^"]*)"\s*-->'
)
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")
SLOW_WPM = 130
FAST_WPM = 150
MAX_TOTAL_SECONDS = 9 * 60 + 30
BUDGET_TOLERANCE = 1.10


@dataclass
class Section:
    """One timed narration section."""

    section_id: str
    budget: int
    title: str
    words: list[str] = field(default_factory=list)
    line_number: int = 0


def parse_sections(text: str) -> list[Section]:
    """Parse section markers and collect blockquote narration."""
    sections: list[Section] = []
    current: Section | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        marker = MARKER_RE.search(line)
        if marker:
            current = Section(
                section_id=marker.group("id"),
                budget=int(marker.group("budget")),
                title=marker.group("title"),
                line_number=line_number,
            )
            sections.append(current)
            continue
        stripped = line.strip()
        if stripped.startswith(">"):
            if current is None:
                raise ValueError(f"narration before the first section marker at line {line_number}")
            narration = stripped.lstrip(">").strip()
            if narration:
                current.words.extend(WORD_RE.findall(narration))
    return sections


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SCRIPT
    if not path.exists():
        print(f"FAIL: {path} does not exist", file=sys.stderr)
        return 1

    try:
        sections = parse_sections(path.read_text(encoding="utf-8"))
    except ValueError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    if not sections:
        print("FAIL: no section markers found", file=sys.stderr)
        return 1

    print(f"video timing estimate: {path}")
    print(f"pace: {SLOW_WPM}-{FAST_WPM} words per minute; tolerance: +10% per section")
    print()
    print(f"{'ID':<4} {'Words':>6} {'@130s':>7} {'@150s':>7} {'Budget':>7} {'Status':>10}  Title")
    print("-" * 86)

    failures: list[str] = []
    total_words = 0
    total_budget = 0
    for section in sections:
        words = len(section.words)
        total_words += words
        total_budget += section.budget
        slow_seconds = words / SLOW_WPM * 60
        fast_seconds = words / FAST_WPM * 60
        allowed = section.budget * BUDGET_TOLERANCE
        status = "ok"
        if words == 0:
            status = "EMPTY"
            failures.append(f"{section.section_id}: no narration words")
        elif slow_seconds > allowed:
            status = "OVER"
            failures.append(
                f"{section.section_id}: {slow_seconds:.0f}s at {SLOW_WPM} wpm "
                f"exceeds {section.budget}s budget by >10%"
            )
        print(
            f"{section.section_id:<4} {words:>6} {slow_seconds:>6.0f}s {fast_seconds:>6.0f}s "
            f"{section.budget:>6}s {status:>10}  {section.title}"
        )

    slow_total = total_words / SLOW_WPM * 60
    fast_total = total_words / FAST_WPM * 60
    print("-" * 86)
    print(
        f"TOTAL {total_words} words · {slow_total:.0f}s at {SLOW_WPM} wpm "
        f"({slow_total / 60:.1f} min) · {fast_total:.0f}s at {FAST_WPM} wpm"
    )
    print(f"declared spoken budget: {total_budget}s ({total_budget / 60:.1f} min)")
    print(f"target ceiling: {MAX_TOTAL_SECONDS}s (9:30)")

    if total_budget > MAX_TOTAL_SECONDS:
        failures.append(
            f"declared budgets sum to {total_budget}s, above the {MAX_TOTAL_SECONDS}s target"
        )
    if slow_total > MAX_TOTAL_SECONDS:
        failures.append(
            f"narration is {slow_total:.0f}s at {SLOW_WPM} wpm, above the {MAX_TOTAL_SECONDS}s target"
        )

    if failures:
        print("\nFAIL:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("\nok: every section is within its budget and the total is under 9:30 at 130 wpm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
