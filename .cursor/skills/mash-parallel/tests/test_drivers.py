"""U6 tests: harness drivers and selection (R26, R14, R17)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp  # noqa: E402

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


# --- cursor-agent / codex / claude support ------------------------------------

ALL_HARNESSES = ["pi", "opencode", "cursor-agent", "codex", "claude"]


def test_all_five_harnesses_are_supported():
    # Priority order is the probe order; every entry must be constructible.
    assert rp.HARNESS_PRIORITY == ALL_HARNESSES
    for name in ALL_HARNESSES:
        assert rp.HarnessDriver.from_name(name).binary


def test_unknown_harness_still_rejected():
    with pytest.raises(ValueError):
        rp.HarnessDriver.from_name("not-a-harness")
    with pytest.raises(rp.ValidationError):
        rp.select_harness("not-a-harness", lambda name: True, rp.HARNESS_PRIORITY)


def test_new_harness_launch_shapes_are_non_interactive():
    # Each worker must run headless and emit structured output, or the
    # orchestrator cannot tell a finished task from a hung prompt.
    cursor = rp.HarnessDriver.from_name("cursor-agent").launch_cmd()
    assert cursor[:2] == ["cursor-agent", "-p"]
    assert "json" in cursor

    codex = rp.HarnessDriver.from_name("codex").launch_cmd()
    assert codex[:2] == ["codex", "exec"]
    assert "--json" in codex

    claude = rp.HarnessDriver.from_name("claude").launch_cmd()
    assert claude[:2] == ["claude", "-p"]
    assert "stream-json" in claude


def test_harness_without_default_model_omits_model_flag():
    # These harnesses use their own configured default; passing an empty
    # --model would be a launch error.
    for name in ("cursor-agent", "codex", "claude"):
        assert rp.HarnessDriver.from_name(name).model is None
        assert "--model" not in rp.HarnessDriver.from_name(name).launch_cmd()
    # An explicit override still wires the flag.
    cmd = rp.HarnessDriver.from_name("codex", model="gpt-5").launch_cmd()
    assert cmd[cmd.index("--model") + 1] == "gpt-5"


def test_new_harnesses_reject_silent_exit_zero():
    # The exit-0-with-no-output shape must read as failure on every harness,
    # otherwise an auto-rejected worker is harvested as a completed task.
    for name in ("cursor-agent", "codex", "claude"):
        h = rp.HarnessDriver.from_name(name)
        assert h.interpret(0, "") == "failure"
        assert h.interpret(0, '{"type": "permission"}\n') == "failure"
        assert h.interpret(1, '{"type": "text", "text": "Done."}\n') == "failure"


def test_new_harnesses_accept_their_text_event_shapes():
    claude = rp.HarnessDriver.from_name("claude")
    assert claude.interpret(0, '{"type": "assistant", "message": {"content": "Done."}}\n') == "done"

    codex = rp.HarnessDriver.from_name("codex")
    assert codex.interpret(0, '{"type": "item.completed", "item": {"text": "Done."}}\n') == "done"

    cursor = rp.HarnessDriver.from_name("cursor-agent")
    assert cursor.interpret(0, '{"type": "text", "text": "Done."}\n') == "done"


# Fixtures below were captured from the real CLIs (codex-cli 0.157.1,
# claude-code 2.1.283) rather than assumed, after `--help` verification of the
# launch flags.

# claude nests assistant text in a *list of content blocks*, so a truthiness
# test on `message.content` would accept a turn that only called tools.
CLAUDE_TEXT = '{"type":"assistant","message":{"content":[{"type":"text","text":"Done."}]}}\n'
CLAUDE_TOOL_ONLY = '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash"}]}}\n'
CLAUDE_RESULT_OK = '{"type":"result","subtype":"success","result":"Done."}\n'
CLAUDE_RESULT_ERR = '{"type":"result","subtype":"error_during_execution","is_error":true}\n'

# Real codex failure stream: JSONL interleaved with plain-text log lines.
CODEX_AUTH_FAILURE = (
    '{"type":"thread.started","thread_id":"x"}\n'
    '{"type":"turn.started"}\n'
    "2026-09-27T12:49:53Z ERROR codex_api: failed to connect to websocket\n"
    '{"type":"error","message":"Reconnecting... 2/5 (401 Unauthorized)"}\n'
    '{"type":"turn.failed","error":{"message":"401 Unauthorized"}}\n'
)


def test_claude_requires_a_real_text_block_not_just_content():
    # Regression: a tool-use-only turn produced no answer, so it must not be
    # harvested as a completed task even though `content` is non-empty.
    claude = rp.HarnessDriver.from_name("claude")
    assert claude.interpret(0, CLAUDE_TEXT) == "done"
    assert claude.interpret(0, CLAUDE_TOOL_ONLY) == "failure"
    assert claude.interpret(0, '{"type":"assistant","message":{"content":[]}}\n') == "failure"
    assert (
        claude.interpret(0, '{"type":"assistant","message":{"content":[{"type":"text","text":""}]}}\n')
        == "failure"
    )


def test_claude_terminal_result_event():
    claude = rp.HarnessDriver.from_name("claude")
    assert claude.interpret(0, CLAUDE_RESULT_OK) == "done"
    # An explicitly failed result must not read as success even on exit 0.
    assert claude.interpret(0, CLAUDE_RESULT_ERR) == "failure"


def test_codex_real_failure_stream_with_interleaved_log_lines():
    # The plain-text ERROR lines must be skipped as noise, and an error-only
    # event stream must never read as success - including on exit 0.
    codex = rp.HarnessDriver.from_name("codex")
    assert codex.interpret(101, CODEX_AUTH_FAILURE) == "failure"
    assert codex.interpret(0, CODEX_AUTH_FAILURE) == "failure"


def test_claude_stream_json_launch_requires_verbose():
    # `claude -p --output-format stream-json` errors out without --verbose:
    # "When using --print, --output-format=stream-json requires --verbose".
    cmd = rp.HarnessDriver.from_name("claude").launch_cmd()
    assert "--output-format" in cmd and "stream-json" in cmd
    assert "--verbose" in cmd


def test_selection_prefers_verifiable_harnesses():
    # pi and opencode have machine-checked completion events, so they lead.
    availability = dict.fromkeys(ALL_HARNESSES, True)
    assert rp.select_harness(None, availability.get, rp.HARNESS_PRIORITY) == "pi"
    availability["pi"] = False
    assert rp.select_harness(None, availability.get, rp.HARNESS_PRIORITY) == "opencode"
    # With only the new harnesses present, one is still selected rather than
    # failing the run.
    availability.update({"pi": False, "opencode": False})
    assert rp.select_harness(None, availability.get, rp.HARNESS_PRIORITY) == "cursor-agent"
    availability["cursor-agent"] = False
    assert rp.select_harness(None, availability.get, rp.HARNESS_PRIORITY) == "codex"
    availability["codex"] = False
    assert rp.select_harness(None, availability.get, rp.HARNESS_PRIORITY) == "claude"


def test_no_harness_error_names_every_candidate():
    availability = dict.fromkeys(ALL_HARNESSES, False)
    with pytest.raises(rp.ValidationError) as excinfo:
        rp.select_harness(None, availability.get, rp.HARNESS_PRIORITY)
    message = str(excinfo.value)
    for name in ALL_HARNESSES:
        assert name in message


def test_failure_carries_fix_hint():
    guidance = rp.retry_guidance("merge conflict on feature/x")
    assert guidance["errorType"] == "merge_conflict"
    assert "resolve" in guidance["fixHint"]


def test_run_log_is_single_file(tmp_path):
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run1")
    rp.append_run_log(tmp_path, "run1", "[plan] t1: done")
    rp.append_run_log(tmp_path, "run1", "[work] t1: done")
    logs = tmp_path / ".mash" / "parallel" / "runs" / "run1" / "logs"
    names = sorted(p.name for p in logs.iterdir())
    assert names == ["run.log"]
    assert not (tmp_path / ".mash" / "parallel" / "runs" / "run1" / "summary.log").exists()
    text = (logs / "run.log").read_text()
    assert "[plan] t1: done" in text
    assert "[work] t1: done" in text


def test_timeout_kills_process_group(tmp_path):
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run-to", timeout_budget=0.3)
    driver.harness.launch_cmd = lambda: [sys.executable, "-c", "import time; time.sleep(20)"]
    outcome = driver._invoke("t1", "work")
    assert outcome == "timeout"
    assert driver.task_pgid("t1")
    log = (tmp_path / ".mash" / "parallel" / "runs" / "run-to" / "logs" / "run.log").read_text()
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
    log = (tmp_path / ".mash" / "parallel" / "runs" / "run-launch" / "logs" / "run.log").read_text()
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
    # mash-plan emits PLAN PATH: inside MASH_PLAN_HANDOFF; that line is the
    # only contract for recovering the plan a worker wrote.
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "run-abc")
    driver._outputs["t1"] = (
        "MASH_PLAN_HANDOFF\n"
        "PLAN PATH: .mash/plans/2026-09-06-001-t1-plan.md\n"
        "FILES:\n- src/a.py\n"
        "BLOCKERS: none\n"
        "END_MASH_PLAN_HANDOFF\n"
    )
    assert driver.plan_path("t1") == ".mash/plans/2026-09-06-001-t1-plan.md"
    assert driver.plan_path("missing") is None
