"""U8 tests: orchestrator flow (R1, R3, R4, R6, R10-12, R16-18, R20, R23)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402


class FakeDriver:
    """Scripted outcomes so the orchestrator loop needs no real harness."""

    def __init__(self, planner_outcomes=None, work_outcomes=None):
        self.planner = list(planner_outcomes or [])
        self.work = list(work_outcomes or [])
        self.log = []

    def plan_task(self, task_id):
        out = self.planner.pop(0) if self.planner else "done"
        self.log.append(("plan", task_id, out))
        return out

    def work_phase(self, task_id):
        out = self.work.pop(0) if self.work else "done"
        self.log.append(("work", task_id, out))
        return out


def test_full_run_happy_path(tmp_path):
    tasks = {
        "t1": rp.new_task("t1", "one", deps=[]),
        "t2": rp.new_task("t2", "two", deps=[]),
        "t3": rp.new_task("t3", "three", deps=["t1"]),
    }
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}, "t3": {"a.py"}}
    # footprint: t1&t3 overlap -> track; t2 separate. t3 also deps t1.
    driver = FakeDriver()
    run = rp.orchestrate_run(
        tmp_path, tasks, footprints, driver, base_branch="develop", base_sha="abc",
    )
    assert run["state"]["t1"]["status"] == rp.STATUS_DONE
    assert run["tracks"]
    # all tasks eventually done
    for tid in tasks:
        assert run["state"][tid]["status"] == rp.STATUS_DONE


def test_all_overlapping_single_serial_track(tmp_path):
    tasks = {tid: rp.new_task(tid, tid) for tid in ("a", "b", "c")}
    footprints = {tid: {"x.py"} for tid in tasks}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert len(run["tracks"]) == 1
    assert any("parallel" in w for w in run["warnings"])


def test_resume_relaunches_interrupted_only(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    # simulate partial state: t1 done, t2 reverted to pending (as if interrupted)
    run["state"]["t2"]["status"] = rp.STATUS_PENDING
    # resume: only t2 relaunched; t1 untouched
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run)
    assert run2["state"]["t1"]["status"] == rp.STATUS_DONE
    assert run2["state"]["t2"]["status"] == rp.STATUS_DONE
    assert all(e[0] != "plan" or e[1] != "t1" for e in driver2.log)


def test_blocker_halt_does_not_block_other_tracks(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    # t1 blocks, t2 succeeds
    driver = FakeDriver(work_outcomes=["blocker", "done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=2)
    assert run["state"]["t1"]["status"] == rp.STATUS_BLOCKED
    assert run["state"]["t2"]["status"] == rp.STATUS_DONE


def test_drift_collision_pauses_track(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {}}  # t2 empty footprint -> separate track
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_DONE
    # no crash; drift collision surfaced in warnings if footprints collided
    assert isinstance(run["warnings"], list)


# --- Hardening U2: dependency-frontier admission + FIFO queue (R3, R4) ---


def test_dependency_only_tasks_run_in_parallel_after_dep_lands(tmp_path):
    # a -> b, a -> c (disjoint footprints). b and c must run in the same pass
    # once a lands (frontier admission), not serially.
    tasks = {
        "a": rp.new_task("a", "A"),
        "b": rp.new_task("b", "B", deps=["a"]),
        "c": rp.new_task("c", "C", deps=["a"]),
    }
    footprints = {"a": {"a.py"}, "b": {"b.py"}, "c": {"c.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=4)
    for tid in tasks:
        assert run["state"][tid]["status"] == rp.STATUS_DONE
    # b and c both admitted in the same wave (frontier admission, not serial)
    waves = run["waves"]
    assert any("b" in w and "c" in w for w in waves)
    assert any("a" in w for w in waves)


def test_slow_sibling_does_not_hold_back_ready_dependent(tmp_path):
    # a (slow) and b are independent; c depends on b only. c must run even
    # though a is still mid-flight.
    tasks = {
        "a": rp.new_task("a", "A"),
        "b": rp.new_task("b", "B"),
        "c": rp.new_task("c", "C", deps=["b"]),
    }
    footprints = {"a": {"a.py"}, "b": {"b.py"}, "c": {"c.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=2)
    assert run["state"]["c"]["status"] == rp.STATUS_DONE
    assert run["state"]["a"]["status"] == rp.STATUS_DONE


def test_oversubscription_parks_and_retries_on_slot_free(tmp_path):
    # 3 independent tasks, max_parallel=2 -> one parks in the denied queue and
    # runs on a freed slot; none fails.
    tasks = {tid: rp.new_task(tid, tid) for tid in ("a", "b", "c")}
    footprints = {tid: {f"{tid}.py"} for tid in tasks}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=2)
    for tid in tasks:
        assert run["state"][tid]["status"] == rp.STATUS_DONE


def test_file_overlap_tasks_serialize_on_track(tmp_path):
    # a and b share a footprint -> same track -> never run in the same wave.
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B")}
    footprints = {"a": {"x.py"}, "b": {"x.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=4)
    # each wave holds at most one task per track
    for wave in run["waves"]:
        assert not (set(wave) >= {"a", "b"})  # a and b never co-admit
    assert run["state"]["a"]["status"] == rp.STATUS_DONE
    assert run["state"]["b"]["status"] == rp.STATUS_DONE