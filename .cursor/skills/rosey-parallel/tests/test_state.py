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


def test_hung_but_alive_owner_reaped(tmp_path):
    p = tmp_path / "locks" / "t1.lock"
    # live pid but heartbeat older than the stale window -> hung-but-alive
    rp.atomic_write_json(p, {
        "ownerTag": "hung", "pid": __import__("os").getpid(),
        "acquiredAt": "2020-01-01T00:00:00Z", "lastHeartbeat": "2020-01-01T00:00:00Z",
    })
    assert rp.detect_stale_lock(json.loads(p.read_text())) is True
    assert rp.acquire_lock(p, "orchestrator") is True


def test_heartbeat_refreshes_lock(tmp_path):
    p = tmp_path / "locks" / "t1.lock"
    rp.acquire_lock(p, "orchestrator")
    rp.atomic_write_json(p, {
        "ownerTag": "orchestrator", "pid": __import__("os").getpid(),
        "acquiredAt": "2020-01-01T00:00:00Z", "lastHeartbeat": "2020-01-01T00:00:00Z",
    })
    rp.heartbeat_lock(p)
    assert rp.detect_stale_lock(json.loads(p.read_text())) is False


def test_result_claimed_exactly_once(tmp_path):
    rd = tmp_path / "run1"
    rd.mkdir(parents=True)
    (rd / "t1.json").write_text('{"ok": true}')
    first = rp.claim_result(rd, "t1")
    assert first is not None and first.name == "t1.json"
    assert (rd / "processed" / "t1.json").exists()
    # second claim returns None (already processed)
    assert rp.claim_result(rd, "t1") is None


def test_result_claim_resume_completes_mid_claim(tmp_path):
    rd = tmp_path / "run1"
    rd.mkdir(parents=True)
    # crash left a .delivering- slot; resume completes it, never double-processes
    (rd / ".delivering-t1.json").write_text('{"ok": true}')
    claimed = rp.claim_result(rd, "t1")
    assert claimed is not None
    assert (rd / "processed" / "t1.json").exists()
    assert not (rd / ".delivering-t1.json").exists()
    assert rp.claim_result(rd, "t1") is None


def test_result_claim_absent_returns_none(tmp_path):
    rd = tmp_path / "run1"
    rd.mkdir(parents=True)
    assert rp.claim_result(rd, "missing") is None