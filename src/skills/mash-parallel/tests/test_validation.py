"""U2 tests: input validation (R1, R2)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp  # noqa: E402


def _ok_tasks():
    return [
        {"id": "t1", "goal": "first", "deps": []},
        {"id": "t2", "goal": "second", "deps": ["t1"]},
        {"id": "t3", "harness": "pi", "goal": "third", "deps": []},
    ]


def test_happy_path_validates_and_normalizes_deps():
    validated = rp.validate_inputs(_ok_tasks(), {"base_branch": "develop"})
    assert [t["id"] for t in validated] == ["t1", "t2", "t3"]
    assert validated[1]["deps"] == ["t1"]
    assert validated[0]["deps"] == []


def test_empty_task_list_errors():
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs([], {"base_branch": "develop"})
    assert "empty" in str(exc.value).lower()


def test_single_task_valid():
    validated = rp.validate_inputs(
        [{"id": "solo", "goal": "only", "deps": []}], {"base_branch": "develop"}
    )
    assert len(validated) == 1


def test_duplicate_ids_named():
    tasks = [
        {"id": "t1", "goal": "a", "deps": []},
        {"id": "t1", "goal": "b", "deps": []},
    ]
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs(tasks, {"base_branch": "develop"})
    assert "t1" in str(exc.value)


def test_unknown_dep_named():
    tasks = [{"id": "t1", "goal": "a", "deps": ["ghost"]}]
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs(tasks, {"base_branch": "develop"})
    assert "ghost" in str(exc.value)


def test_self_dep_named():
    tasks = [{"id": "t1", "goal": "a", "deps": ["t1"]}]
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs(tasks, {"base_branch": "develop"})
    assert "t1" in str(exc.value) and "self" in str(exc.value).lower()


def test_malformed_entry_named():
    tasks = [{"id": "t1", "deps": []}]  # missing goal
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs(tasks, {"base_branch": "develop"})
    assert "t1" in str(exc.value)


def test_cycle_members_listed():
    tasks = [
        {"id": "t1", "goal": "a", "deps": ["t2"]},
        {"id": "t2", "goal": "b", "deps": ["t1"]},
    ]
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs(tasks, {"base_branch": "develop"})
    assert "t1" in str(exc.value) and "t2" in str(exc.value)


def test_all_violations_in_one_pass():
    tasks = [
        {"id": "t1", "goal": "a", "deps": ["t1"]},
        {"id": "t1", "goal": "a", "deps": ["ghost"]},
        {"id": "t2", "deps": []},
    ]
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs(tasks, {"base_branch": "develop"})
    msg = str(exc.value)
    assert "ghost" in msg and "t2" in msg and "self" in msg.lower()
    # cycle check skipped when ids invalid; not required in message
    assert isinstance(exc.value.violations, list) and len(exc.value.violations) >= 3