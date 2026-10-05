"""U4 tests: deterministic sequencer (R7, R8, R9)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp  # noqa: E402


def test_two_overlapping_pairs_make_two_tracks():
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B"),
             "c": rp.new_task("c", "C"), "d": rp.new_task("d", "D")}
    # a overlaps b; c overlaps d; disjoint pairs
    schedule = rp.schedule(
        tasks,
        {"a": {"x.py"}, "b": {"x.py"}, "c": {"y.py"}, "d": {"y.py"}},
    )
    assert len(schedule["tracks"]) == 2
    for trk in schedule["tracks"]:
        assert len(trk["tasks"]) == 2


def test_declared_dep_does_not_force_same_track():
    # Hardening U2: track membership is footprint-overlap only. A dependency
    # edge alone does not union tasks into one track; the frontier admission
    # loop handles dependency ordering.
    tasks = {"a": rp.new_task("a", "A", deps=["b"]), "b": rp.new_task("b", "B")}
    schedule = rp.schedule(tasks, {"a": {"x.py"}, "b": {"y.py"}})
    assert len(schedule["tracks"]) == 2  # disjoint footprints -> separate tracks


def test_single_task_singleton_track():
    tasks = {"a": rp.new_task("a", "A")}
    schedule = rp.schedule(tasks, {"a": {"x.py"}})
    assert len(schedule["tracks"]) == 1
    assert schedule["tracks"][0]["tasks"] == ["a"]


def test_all_overlapping_single_serial_track():
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B"),
             "c": rp.new_task("c", "C")}
    schedule = rp.schedule(tasks, {"a": {"x.py"}, "b": {"x.py"}, "c": {"x.py"}})
    assert len(schedule["tracks"]) == 1
    assert set(schedule["tracks"][0]["tasks"]) == {"a", "b", "c"}
    assert any(w for w in schedule["warnings"] if "parallel" in w.lower())


def test_empty_footprint_singleton_with_warning():
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B")}
    schedule = rp.schedule(tasks, {"a": set(), "b": {"y.py"}})
    assert len(schedule["tracks"]) == 2
    assert any("footprint" in w.lower() for w in schedule["warnings"])


def test_dep_cycle_fails_loudly():
    tasks = {"a": rp.new_task("a", "A", deps=["b"]),
             "b": rp.new_task("b", "B", deps=["c"]),
             "c": rp.new_task("c", "C", deps=["a"])}
    with pytest.raises(rp.ValidationError) as exc:
        rp.schedule(tasks, {"a": {"1"}, "b": {"2"}, "c": {"3"}})
    assert "cycle" in str(exc.value).lower()
    assert "a" in str(exc.value)


def test_cycle_detection_shared_helper():
    # P2-11: validate_inputs and schedule share one canonical cycle helper
    # (_find_cycles); both still detect a cycle after the collapse.
    tasks = [
        {"id": "a", "goal": "A", "deps": ["b"]},
        {"id": "b", "goal": "B", "deps": ["a"]},
    ]
    with pytest.raises(rp.ValidationError) as exc:
        rp.validate_inputs(tasks, {})
    assert "cycle" in str(exc.value).lower()
    # schedule() also routes through the same helper.
    sched_tasks = {"a": rp.new_task("a", "A", deps=["b"]),
                   "b": rp.new_task("b", "B", deps=["a"])}
    with pytest.raises(rp.ValidationError) as exc2:
        rp.schedule(sched_tasks, {"a": {"1"}, "b": {"2"}})
    assert "cycle" in str(exc2.value).lower()


def test_cross_component_dep_merges_components():
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B", deps=["d"]),
             "c": rp.new_task("c", "C"), "d": rp.new_task("d", "D")}
    # a-c overlap (component 1), d alone (component 2), b depends on d
    schedule = rp.schedule(
        tasks,
        {"a": {"x.py"}, "b": {"y.py"}, "c": {"x.py"}, "d": {"z.py"}},
    )
    # Hardening U2: tracks are footprint-overlap only. a,c share x.py -> one
    # track; b,d have disjoint footprints -> separate tracks (dependency edge
    # does NOT union them).
    assert len(schedule["tracks"]) == 3
    tracks_by_task = {}
    for trk in schedule["tracks"]:
        for t in trk["tasks"]:
            tracks_by_task[t] = trk["track_id"]
    assert tracks_by_task["a"] == tracks_by_task["c"]
    assert tracks_by_task["b"] != tracks_by_task["d"]  # dep edge no longer unions


def test_deterministic_identical_inputs():
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B", deps=["d"]),
             "c": rp.new_task("c", "C"), "d": rp.new_task("d", "D")}
    footprints = {
        "a": {"x.py"}, "b": {"y.py"}, "c": {"x.py"}, "d": {"z.py"}
    }
    s1 = rp.schedule(tasks, dict(footprints))
    s2 = rp.schedule(tasks, dict(footprints))
    assert s1 == s2


def test_tie_break_lexicographic():
    tasks = {"z": rp.new_task("z", "Z"), "a": rp.new_task("a", "A")}
    # a and z both empty footprint -> singleton tracks; tracks by smallest id
    schedule = rp.schedule(tasks, {"z": set(), "a": set()})
    order = [trk["track_id"] for trk in schedule["tracks"]]
    # both singletons; deterministic order by smallest task id
    seq = [trk["tasks"][0] for trk in schedule["tracks"]]
    assert seq == sorted(seq)


# --- Hardening U2: track membership is footprint-overlap only (R3) ---


def test_dependency_only_tasks_land_in_separate_tracks():
    # Two tasks with a dependency edge but disjoint footprints -> separate
    # tracks, so the frontier admission loop can run them in parallel once
    # the dependency lands.
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B", deps=["a"])}
    schedule = rp.schedule(tasks, {"a": {"x.py"}, "b": {"y.py"}})
    assert len(schedule["tracks"]) == 2
    tracks_by_task = {t: trk["track_id"] for trk in schedule["tracks"] for t in trk["tasks"]}
    assert tracks_by_task["a"] != tracks_by_task["b"]


def test_file_overlap_still_serializes_on_track():
    # File-overlap tasks stay serialized on a single track (collision safety).
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B")}
    schedule = rp.schedule(tasks, {"a": {"x.py"}, "b": {"x.py"}})
    assert len(schedule["tracks"]) == 1
    assert set(schedule["tracks"][0]["tasks"]) == {"a", "b"}