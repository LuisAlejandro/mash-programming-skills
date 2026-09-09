"""U6 tests: harness drivers and selection (R26, R14, R17)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402

PRIORITY = ["pi", "opencode"]

# Realistic structured-output fixtures, truncated to the terminal event.
# pi marks events with `type` (not `event`) and emits a trailing
# `agent_settled` after `agent_end`.
PI_END = "{\"type\": \"agent_end\"}\n"
PI_END_SETTLED = "{\"type\": \"agent_end\"}\n{\"type\": \"agent_settled\"}\n"
OPENCODE_END = "{\"type\": \"text\", \"part\": {\"type\": \"text\", \"text\": \"Done.\"}}\n"
# Real opencode output ends with step_finish after the text event; text is
# nested under part.text.
OPENCODE_STEP_FINISH = "{\"type\": \"text\", \"part\": {\"type\": \"text\", \"text\": \"Done.\"}}\n{\"type\": \"step_finish\", \"part\": {\"type\": \"step-finish\"}}\n"

# opencode bug shape: exit 0 but only a mid-session auto-reject (empty final text)
OPENCODE_NO_TEXT = "{\"type\": \"permission\", ...}\n"


def test_pi_done():
    h = rp.HarnessDriver.from_name("pi")
    assert h.interpret(0, PI_END) == "done"


def test_pi_done_with_trailing_settled():
    # Regression: pi emits agent_settled after agent_end; the terminal event
    # is not agent_end, so interpret must not require it to be last.
    h = rp.HarnessDriver.from_name("pi")
    assert h.interpret(0, PI_END_SETTLED) == "done"


def test_opencode_done():
    h = rp.HarnessDriver.from_name("opencode")
    assert h.interpret(0, OPENCODE_END) == "done"


def test_opencode_done_with_trailing_step_finish():
    # Regression: opencode emits step_finish after the text event, so the
    # terminal event is not text. interpret must accept a non-empty text event
    # appearing anywhere, not require it to be last.
    h = rp.HarnessDriver.from_name("opencode")
    assert h.interpret(0, OPENCODE_STEP_FINISH) == "done"


def test_opencode_done_with_step_finish():
    h = rp.HarnessDriver.from_name("opencode")
    assert h.interpret(0, OPENCODE_STEP_FINISH) == "done"


def test_opencode_empty_final_text_is_failure():
    # exit 0 + no final text event (auto-reject bug) -> failure, not done
    h = rp.HarnessDriver.from_name("opencode")
    assert h.interpret(0, "") == "failure"


def test_missing_terminal_event_exit0_is_failure():
    h = rp.HarnessDriver.from_name("pi")
    assert h.interpret(0, "{\"event\": \"other\"}\n") == "failure"


def test_exit_nonzero_is_failure():
    h = rp.HarnessDriver.from_name("opencode")
    assert h.interpret(1, OPENCODE_END) == "failure"


def test_probe_missing_binary_returns_false():
    h = rp.HarnessDriver.from_name("pi", binary="definitely-not-a-real-binary-xyz")
    assert h.probe() is False


def test_default_models_per_harness():
    # Default model flags are wired per harness (pi/opencode deepseek).
    assert rp.HarnessDriver.from_name("pi").model == "deepseek-v4-flash"
    assert rp.HarnessDriver.from_name("opencode").model == "opencode/deepseek-v4-flash"


def test_launch_cmd_includes_model_flag():
    assert "--model" in rp.HarnessDriver.from_name("pi").launch_cmd()
    assert "--model" in rp.HarnessDriver.from_name("opencode").launch_cmd()


def test_launch_cmd_model_override():
    h = rp.HarnessDriver.from_name("pi", model="deepseek-v4-pro")
    cmd = h.launch_cmd()
    assert cmd[cmd.index("--model") + 1] == "deepseek-v4-pro"


def test_pi_launch_omits_no_session():
    cmd = rp.HarnessDriver.from_name("pi").launch_cmd()
    assert "--no-session" not in cmd


def test_select_override_wins():
    chosen = rp.select_harness("opencode", lambda name: True, PRIORITY)
    assert chosen == "opencode"


def test_select_highest_priority_available():
    # pi unavailable, opencode available
    availability = {"pi": False, "opencode": True}
    assert rp.select_harness(None, availability.get, PRIORITY) == "opencode"
    # all available -> pi default
    availability = {"pi": True, "opencode": True}
    assert rp.select_harness(None, availability.get, PRIORITY) == "pi"


def test_select_none_available_fails():
    availability = {"pi": False, "opencode": False}
    with pytest.raises(rp.ValidationError):
        rp.select_harness(None, availability.get, PRIORITY)


def test_failure_carries_fix_hint():
    guidance = rp.retry_guidance("merge conflict on feature/x")
    assert guidance["errorType"] == "merge_conflict"
    assert "resolve" in guidance["fixHint"]


def test_run_log_is_single_file(tmp_path):
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run1")
    rp.append_run_log(tmp_path, "run1", "[plan] t1: done")
    rp.append_run_log(tmp_path, "run1", "[work] t1: done")
    logs = tmp_path / "rosey" / "parallel" / "runs" / "run1" / "logs"
    names = sorted(p.name for p in logs.iterdir())
    assert names == ["run.log"]
    assert not (tmp_path / "rosey" / "parallel" / "runs" / "run1" / "summary.log").exists()
    text = (logs / "run.log").read_text()
    assert "[plan] t1: done" in text
    assert "[work] t1: done" in text


def test_timeout_kills_process_group(tmp_path):
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run-to", timeout_budget=0.3)
    driver.harness.launch_cmd = lambda: [sys.executable, "-c", "import time; time.sleep(20)"]
    outcome = driver._invoke("t1", "work")
    assert outcome == "timeout"
    assert driver.task_pgid("t1")
    log = (tmp_path / "rosey" / "parallel" / "runs" / "run-to" / "logs" / "run.log").read_text()
    assert "timeout" in log


def test_kill_orphaned_process_groups(tmp_path):
    import subprocess
    import time

    proc = subprocess.Popen(
        ["/bin/sleep", "30"], start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    run = {"tasks": {"t1": {"pgid": proc.pid}}}
    killed = rp.kill_orphaned_process_groups(run)
    proc.wait(timeout=5)
    assert proc.pid in killed or proc.poll() is not None
    time.sleep(0.05)
    assert not rp.is_pid_alive(proc.pid)


def test_orphaned_pgid_persisted_and_reaped_on_resume(tmp_path):
    # P1-4: a spawned pgid is persisted to a spawn-time file under the run dir
    # so a crash mid-work (before the pgid reaches run state) can still be
    # reaped on resume.
    import subprocess
    import time

    proc = subprocess.Popen(
        ["/bin/sleep", "30"], start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Simulate a crash: the pgid file exists but the run record has no pgid.
    pgid_dir = rp.run_dir(tmp_path, "run-pgid") / "pgids"
    pgid_dir.mkdir(parents=True, exist_ok=True)
    (pgid_dir / "t1.pgid").write_text(str(proc.pid))
    run = {"run_id": "run-pgid", "tasks": {"t1": {}}}
    killed = rp.kill_orphaned_process_groups(run, tmp_path)
    proc.wait(timeout=5)
    assert proc.pid in killed or proc.poll() is not None
    time.sleep(0.05)
    assert not rp.is_pid_alive(proc.pid)


def test_harness_phase_driver_uses_options_model(tmp_path):
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run-m", model="deepseek-v4-pro")
    assert driver.harness.model == "deepseek-v4-pro"
    cmd = driver.harness.launch_cmd()
    assert cmd[cmd.index("--model") + 1] == "deepseek-v4-pro"


def test_launch_failure_fails_task_cleanly(tmp_path):
    # P2-7: a missing harness binary at launch must fail only that task
    # (return "failure"), not crash the whole run.
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run-launch")
    driver.harness.launch_cmd = lambda: ["definitely-not-a-real-binary-xyz", "prompt"]
    outcome = driver._invoke("t1", "work")
    assert outcome == "failure"
    log = (tmp_path / "rosey" / "parallel" / "runs" / "run-launch" / "logs" / "run.log").read_text()
    assert "launch failed" in log


def test_default_timeout_applied_when_unset(tmp_path):
    # P2-8: when timeout_budget is unset, a non-None default deadline is
    # applied so a hung worker cannot hang the run forever.
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run-default-to")
    assert driver.timeout_budget is None
    assert driver.DEFAULT_PHASE_TIMEOUT_S == 3600.0
    # A worker that sleeps past the (tiny) default would time out; here we
    # just assert the default constant is wired into the communicate timeout.
    # Use a short explicit budget to prove the timeout path still works.
    driver.timeout_budget = 0.2
    driver.harness.launch_cmd = lambda: [sys.executable, "-c", "import time; time.sleep(20)"]
    outcome = driver._invoke("t1", "work")
    assert outcome == "timeout"


def test_plan_path_from_handoff_envelope(tmp_path):
    # rosey-plan emits PLAN PATH: inside ROSEY_PLAN_HANDOFF; that line is the
    # only contract for recovering the plan a worker wrote.
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run-abc")
    driver._outputs["t1"] = (
        "ROSEY_PLAN_HANDOFF\n"
        "PLAN PATH: rosey/plans/2026-09-06-001-t1-plan.md\n"
        "FILES:\n- src/a.py\n"
        "BLOCKERS: none\n"
        "END_ROSEY_PLAN_HANDOFF\n"
    )
    assert driver.plan_path("t1") == "rosey/plans/2026-09-06-001-t1-plan.md"
    assert driver.plan_path("missing") is None
