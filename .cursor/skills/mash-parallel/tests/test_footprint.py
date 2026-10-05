"""U3 tests: footprint parser (R5)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp  # noqa: E402


PLAN_WITH_UNITS = """\
---
title: sample
---

# Sample Plan

## Implementation Units

### U1. First unit

- **Goal:** do something
- **Files:** `.cursor/skills/x/scripts/a.py`, `tests/test_a.py`

### U2. Second unit

- **Goal:** do another
- **Files:** `.cursor/skills/x/scripts/a.py` (modify), `tests/test_b.py` (create)
"""


PLAN_NO_FILES = """\
# Plan With No Files Sections

Some prose. No unit headings with files.
"""


PLAN_FILES_EMPTY = """\
### U1. Unit

- **Files:** (none)
"""


def test_happy_path_union_dedup():
    files, warnings = rp.parse_footprint(PLAN_WITH_UNITS)
    assert files == {".cursor/skills/x/scripts/a.py", "tests/test_a.py", "tests/test_b.py"}
    assert warnings == []


def test_no_files_section_yields_empty_with_warning():
    files, warnings = rp.parse_footprint(PLAN_NO_FILES)
    assert files == set()
    assert any("footprint" in w.lower() or "Files" in w for w in warnings)


def test_files_section_with_no_paths_warns():
    files, warnings = rp.parse_footprint(PLAN_FILES_EMPTY)
    assert files == set()
    assert warnings, "empty Files section should warn"


def test_parser_output_feeds_sequencer_shape():
    files, _ = rp.parse_footprint(PLAN_WITH_UNITS)
    # set semantics, feedable as footprint
    assert isinstance(files, set)


def test_backticks_and_annotations_stripped():
    plan = """\
### U1. Unit
- **Files:** `src/main.py` (create), `src/other.py` (modify)
"""
    files, _ = rp.parse_footprint(plan)
    assert files == {"src/main.py", "src/other.py"}