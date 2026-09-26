"""U1 tests: run-state module (R22, R23, R24)."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402


def test_happy_path_roundtrip(tmp_path):
    run = rp.new_run(
        rp.new_run_id(),
        [rp.new_task("t1", "first"), rp.new_task("t2", "second"), rp.new_task("t3", "third")],
        "develop",
        "abc123",
        "pi",
    )
    rp.transition(run["tasks"]["t1"], rp.STATUS_PLANNING)
    rp.transition(run["tasks"]["t1"], rp.STATUS_PLANNED)
    rp.transition(run["tasks"]["t1"], rp.STATUS_GATE_APPROVED)
    rp.transition(run["tasks"]["t1"], rp.STATUS_WORKING)
    rp.transition(run["tasks"]["t1"], rp.STATUS_QA)
    rp.transition(run["tasks"]["t1"]["path"] if False else run["tasks"]["t1"], rp.STATUS_LINT)
    rp.transition(run["tasks"]["t1"], rp.STATUS_DONE)
    path = rp.save_run(tmp_path, run)
    loaded = rp.load_state(path)
    assert loaded["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert loaded["tasks"]["t2"]["status"] == rp.STATUS_PENDING


def test_identical_writes_byte_identical(tmp_path):
    run = rp.new_run(rp.new_run_id(), [rp.new_task("t1", "demo")], "develop", "sha", "pi")
    p1 = rp.save_run(tmp_path, run)
    data1 = p1.read_bytes()
    # Reload to drop in-memory churn, save again.
    loaded = rp.load_state(p1)
    p2 = rp.save_run(tmp_path, loaded)
    assert p1 == p2
    assert p1.read_bytes() == p2.read_bytes()


def test_orchestrate_run_roundtrips_through_save_load(tmp_path):
    # orchestrate_run's record must round-trip through the CLI save->load->resume
    # cycle with the same schema load_run/_validate_state requires
    # (tasks/base_sha_snapshot).
    class _D:
        def __init__(self):
            self.log = []
        def plan_task(self, tid):
            self.log.append(("plan", tid)); return "done"
        def work_phase(self, tid):
            self.log.append(("work", tid)); return "done"
        def qa_phase(self, tid):
            self.log.append(("qa", tid)); return "done"
        def lint_phase(self, tid):
            self.log.append(("lint", tid)); return "done"
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = _D()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
    # save then load must validate (no StateError) and preserve statuses
    path = rp.save_run(tmp_path, run)
    loaded = rp.load_state(path)
    assert loaded["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert loaded["tasks"]["t2"]["status"] == rp.STATUS_DONE
    # resume from the loaded state must work
    driver2 = _D()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=loaded, gate=False)
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_DONE


def test_corrupt_state_json_raises_clear_error(tmp_path):
    p = tmp_path / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not json")
    with pytest.raises(rp.StateError, match="corrupt state JSON"):
        rp.load_state(p)


def test_missing_state_file_raises_clear_error(tmp_path):
    with pytest.raises(rp.StateError, match="cannot read state file"):
        rp.load_state(tmp_path / "missing" / "state.json")


def test_invalid_transition_rejected():
    run = rp.new_run(rp.new_run_id(), [rp.new_task("t1", "demo")], "develop", "sha", "pi")
    rp.transition(run["tasks"]["t1"], rp.STATUS_PLANNING)
    rp.transition(run["tasks"]["t1"], rp.STATUS_PLANNED)
    rp.transition(run["tasks"]["t1"], rp.STATUS_GATE_APPROVED)
    rp.transition(run["tasks"]["t1"], rp.STATUS_WORKING)
    rp.transition(run["tasks"]["t1"], rp.STATUS_QA)
    rp.transition(run["tasks"]["t1"], rp.STATUS_LINT)
    rp.transition(run["tasks"]["t1"], rp.STATUS_DONE)
    with pytest.raises(rp.StateError, match="invalid transition 'done' -> 'working'"):
        rp.transition(run["tasks"]["t1"], rp.STATUS_WORKING)


def test_unknown_status_rejected():
    task = rp.new_task("t1", "demo")
    with pytest.raises(rp.StateError, match="unknown status"):
        rp.transition(task, "flying")


def test_done_is_checkpoint_terminal():
    assert rp.STATUS_DONE in rp.TERMINAL_STATUSES
    assert rp.STATUS_INTEGRATED in rp.TERMINAL_STATUSES
    assert rp.STATUS_REPORTED in rp.TERMINAL_STATUSES


def test_reset_task_status_bypasses_transition_table():
    task = rp.new_task("t1", "demo")
    rp.transition(task, rp.STATUS_PLANNING)
    rp.transition(task, rp.STATUS_PLANNED)
    rp.transition(task, rp.STATUS_GATE_APPROVED)
    rp.transition(task, rp.STATUS_WORKING)
    rp.transition(task, rp.STATUS_QA)
    rp.transition(task, rp.STATUS_LINT)
    rp.transition(task, rp.STATUS_DONE)
    rp.reset_task_status(task, rp.STATUS_PENDING)
    assert task["status"] == rp.STATUS_PENDING


def test_illegal_planned_to_qa_raises():
    task = rp.new_task("t1", "demo")
    rp.transition(task, rp.STATUS_PLANNING)
    rp.transition(task, rp.STATUS_PLANNED)
    with pytest.raises(rp.StateError, match="invalid transition 'planned' -> 'qa'"):
        rp.transition(task, rp.STATUS_QA)


def test_state_schema_validation(tmp_path):
    run = rp.new_run(rp.new_run_id(), [rp.new_task("t1", "demo")], "develop", "sha", "pi")
    path = rp.save_run(tmp_path, run)
    data = json.loads(path.read_text())
    data.pop("base_sha_snapshot")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(rp.StateError, match="missing required key"):
        rp.load_state(bad)


def test_task_key_id_mismatch_rejected(tmp_path):
    run = rp.new_run(rp.new_run_id(), [rp.new_task("t1", "demo")], "develop", "sha", "pi")
    path = rp.save_run(tmp_path, run)
    data = json.loads(path.read_text())
    data["tasks"]["t1"]["id"] = "t2"
    bad = tmp_path / "mismatch.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(rp.StateError, match="task key"):
        rp.load_state(bad)


# --- Hardening U1: stale-lock liveness + exactly-once result claim (R1, R2) ---


def test_lock_acquire_release_reacquire(tmp_path):
    p = tmp_path / "locks" / "t1.lock"
    assert rp.acquire_lock(p, "orchestrator") is True
    assert rp.acquire_lock(p, "orchestrator") is False  # held, not stale
    rp.release_lock(p)
    assert rp.acquire_lock(p, "orchestrator") is True


def test_stale_lock_dead_pid_reaped(tmp_path):
    p = tmp_path / "locks" / "t1.lock"
    # dead pid (999999) + old acquiredAt -> stale
    rp.atomic_write_json(p, {
        "ownerTag": "dead", "pid": 999999,
        "acquiredAt": "2020-01-01T00:00:00Z", "lastHeartbeat": "2020-01-01T00:00:00Z",
    })
    assert rp.detect_stale_lock(json.loads(p.read_text())) is True
    assert rp.acquire_lock(p, "orchestrator") is True  # reaped + re-acquired


def test_stale_lock_live_pid_not_reaped(tmp_path):
    p = tmp_path / "locks" / "t1.lock"
    rp.acquire_lock(p, "orchestrator")  # live pid, fresh heartbeat
    assert rp.detect_stale_lock(json.loads(p.read_text())) is False
    assert rp.acquire_lock(p, "other") is False  # never stolen


def test_hung_but_alive_owner_not_reaped(tmp_path):
    # A live owner's lock is never stolen, even if its heartbeat is stale.
    p = tmp_path / "locks" / "t1.lock"
    rp.atomic_write_json(p, {
        "ownerTag": "hung", "pid": __import__("os").getpid(),
        "acquiredAt": "2020-01-01T00:00:00Z", "lastHeartbeat": "2020-01-01T00:00:00Z",
    })
    assert rp.detect_stale_lock(json.loads(p.read_text())) is False
    assert rp.acquire_lock(p, "orchestrator") is False  # live owner, not stolen
