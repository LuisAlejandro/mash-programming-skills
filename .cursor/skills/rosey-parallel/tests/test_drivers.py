"""U6 tests: harness drivers and selection (R26, R14, R17)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402

PRIORITY = ["pi", "opencode", "cursor-agent"]

# Realistic structured-output fixtures, truncated to the terminal event.
PI_END = "{\"event\": \"agent_end\"}\n"
OPENCODE_END = "{\"type\": \"text\", \"text\": \"Done.\"}\n"
CURSOR_END = "{\"type\": \"result\", \"result\": {\"status\": \"ok\"}}\n"

# opencode bug shape: exit 0 but only a mid-session auto-reject (empty final text)
OPENCODE_NO_TEXT = "{\"type\": \"permission\", ...}\n"


def test_pi_done():
    h = rp.HarnessDriver.from_name("pi")
    assert h.interpret(0, PI_END) == "done"


def test_opencode_done():
    h = rp.HarnessDriver.from_name("opencode")
    assert h.interpret(0, OPENCODE_END) == "done"


def test_cursor_done():
    h = rp.HarnessDriver.from_name("cursor-agent")
    assert h.interpret(0, CURSOR_END) == "done"


def test_opencode_empty_final_text_is_failure():
    # exit 0 + no final text event (auto-reject bug) -> failure, not done
    h = rp.HarnessDriver.from_name("opencode")
    assert h.interpret(0, "") == "failure"


def test_missing_terminal_event_exit0_is_failure():
    h = rp.HarnessDriver.from_name("pi")
    assert h.interpret(0, "{\"event\": \"other\"}\n") == "failure"


def test_exit_nonzero_is_failure():
    h = rp.HarnessDriver.from_name("cursor-agent")
    assert h.interpret(1, CURSOR_END) == "failure"


def test_probe_missing_binary_returns_false():
    h = rp.HarnessDriver.from_name("pi", binary="definitely-not-a-real-binary-xyz")
    assert h.probe() is False


def test_select_override_wins():
    chosen = rp.select_harness("opencode", lambda name: True, PRIORITY)
    assert chosen == "opencode"


def test_select_highest_priority_available():
    # pi unavailable, opencode available
    availability = {"pi": False, "opencode": True, "cursor-agent": True}
    assert rp.select_harness(None, availability.get, PRIORITY) == "opencode"
    # all available -> pi default
    availability = {"pi": True, "opencode": True, "cursor-agent": True}
    assert rp.select_harness(None, availability.get, PRIORITY) == "pi"


def test_select_none_available_fails():
    availability = {"pi": False, "opencode": False, "cursor-agent": False}
    with pytest.raises(rp.ValidationError):
        rp.select_harness(None, availability.get, PRIORITY)