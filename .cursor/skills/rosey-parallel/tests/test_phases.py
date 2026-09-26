"""U7 tests: worker prompt contract + phase runners (R13, R14, R15)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402

GOOD_HANDOFF = """\
ROSEY_WORK_HANDOFF
BRANCH: feature/x
FILES_CHANGED:
- a.py
- b/c.py
DONE:
- U1: did a thing
WHAT_WAS_IMPLEMENTED:
one line
END_ROSEY_WORK_HANDOFF
"""

BLOCKED_HANDOFF = """\
ROSEY_WORK_HANDOFF
BLOCKERS:
- db schema unknown
- needs human decision
FILES_CHANGED:
- a.py
END_ROSEY_WORK_HANDOFF
"""


def test_handoff_happy_path_done():
    out = rp.extract_handoff(GOOD_HANDOFF)
    assert out["status"] == "done"
    assert out["files_changed"] == ["a.py", "b/c.py"]
    assert out["blockers"] == []


def test_handoff_with_blockers_is_blocker():
    out = rp.extract_handoff(BLOCKED_HANDOFF)
    assert out["status"] == "blocker"
    assert len(out["blockers"]) == 2


def test_handoff_missing_envelope_is_failure():
    out = rp.extract_handoff("some raw agent output with no envelope")
    assert out["status"] == "failure"


def test_drift_detected_against_live_track():
    touched = {"a.py"}
    other_live_footprints = [{"a.py"}, {"b.py"}]
    collisions = rp.find_drift_collisions(touched, other_live_footprints)
    assert collisions == ["a.py"]


def test_no_drift_when_disjoint():
    touched = {"c.py"}
    other_live_footprints = [{"a.py"}, {"b.py"}]
    assert rp.find_drift_collisions(touched, other_live_footprints) == []


def test_worker_overrides_neutralize_branch_and_sentrux():
    overrides = rp.worker_overrides("the-track-branch")
    assert "branch_setup" not in overrides
    assert overrides["sentrux"] == "skip"
    assert overrides["branch"] == "the-track-branch"
    prompt = rp.load_worker_prompt().format(
        goal="g",
        plan_path="p",
        origin_doc="o",
        track_branch="the-track-branch",
        phase="work",
        qa_diff_base="track-branch-point",
    )
    assert "the-track-branch" in prompt
    assert "do not create `feature/<slug>`" in prompt
    assert "verifies the worktree's branch" in prompt
    assert "branch_setup" not in prompt


def test_worker_overrides_include_diff_base_for_track():
    overrides = rp.worker_overrides("the-track-branch")
    # first task's QA base defaults to the track branch point
    assert overrides["qa_diff_base"] == "track-branch-point"


# --- Hardening U4: evidence-bound QA gate + retry guidance (R7, R8) ---


def test_evidence_present_is_done():
    out = GOOD_HANDOFF + "\nROSEY_EVIDENCE\ntest run: 12 passed\nEND_ROSEY_EVIDENCE\n"
    assert rp.has_evidence(out) is True


def test_evidence_absent_is_not_done():
    # handoff but no evidence artifact -> not done (R7)
    assert rp.has_evidence(GOOD_HANDOFF) is False


def test_evidence_empty_body_is_not_done():
    out = GOOD_HANDOFF + "\nROSEY_EVIDENCE\n\nEND_ROSEY_EVIDENCE\n"
    assert rp.has_evidence(out) is False


def test_retry_guidance_known_pattern():
    g = rp.retry_guidance("error: permission denied while writing file")
    assert g["errorType"] == "permission"
    assert "permission" in g["fixHint"]


def test_retry_guidance_unknown_falls_back_generic():
    g = rp.retry_guidance("some totally unknown failure")
    assert g["errorType"] == "unknown"
    assert "generic" in g["fixHint"]
