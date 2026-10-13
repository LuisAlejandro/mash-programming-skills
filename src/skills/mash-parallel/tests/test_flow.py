"""Hardening U5 tests: flow shape — scaffold phase + parallel verification (R9, R10)."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mash_parallel as rp  # noqa: E402


class FakeFlowDriver:
    """Scripted scaffold + verification outcomes for the flow-shape phases."""

    def __init__(self, scaffold="done", verify=None):
        self.scaffold_outcome = scaffold
        self.verify = dict(verify or {})
        self.log = []

    def scaffold_phase(self):
        self.log.append(("scaffold", self.scaffold_outcome))
        return self.scaffold_outcome

    def verify_phase(self, verifier, tip):
        self.log.append(("verify", verifier, tip))
        return self.verify.get(verifier, "pass")


def test_scaffold_phase_produces_contract_doc():
    driver = FakeFlowDriver(scaffold="done")
    result = rp.run_scaffold(driver, {"t1": rp.new_task("t1", "one")})
    assert result["phase"] == "scaffold"
    assert result["outcome"] == "done"
    assert result["contract_doc"] is not None
    assert result["blockers"] == []


def test_scaffold_phase_blocker_surfaces():
    driver = FakeFlowDriver(scaffold="blocker")
    result = rp.run_scaffold(driver, {"t1": rp.new_task("t1", "one")})
    assert result["outcome"] == "blocker"
    assert result["contract_doc"] is None
    assert result["blockers"]


def test_parallel_verification_fans_out_three_verifiers():
    driver = FakeFlowDriver()
    result = rp.run_parallel_verification(driver, "abc123")
    assert result["phase"] == "parallel_verification"
    assert set(result["verifiers"]) == {"code_review", "test_runner", "architecture"}
    assert result["passed"] is True
    # all three verifiers ran concurrently (recorded in order)
    assert [e[0] for e in driver.log] == ["verify", "verify", "verify"]


def test_parallel_verification_rejection_surfaces():
    driver = FakeFlowDriver(verify={"test_runner": "fail"})
    result = rp.run_parallel_verification(driver, "abc123")
    assert result["passed"] is False
    assert result["rejected"] == ["test_runner"]


def test_parallel_verification_done_counts_as_pass():
    # interpret() returns "done", not "pass", so a real harness verifier
    # would be misread as rejected and re-run forever. Both must count as ok.
    driver = FakeFlowDriver(verify={"code_review": "done", "test_runner": "done", "architecture": "done"})
    result = rp.run_parallel_verification(driver, "abc123")
    assert result["passed"] is True
    assert result["rejected"] == []


def test_parallel_verification_consumes_integrated_tip():
    driver = FakeFlowDriver()
    rp.run_parallel_verification(driver, "integrated-tip-sha")
    assert all(e[2] == "integrated-tip-sha" for e in driver.log)


def test_relocate_qa_artifacts(tmp_path):
    wt = tmp_path / "wt"
    (wt / ".mash" / "qa").mkdir(parents=True)
    (wt / ".mash" / "qa" / "notes.md").write_text("qa\n")
    dest = tmp_path / "run" / "qa" / "t1"
    rp.relocate_qa_artifacts(wt, dest)
    assert not (wt / ".mash" / "qa").exists()
    assert (dest / "qa" / "notes.md").read_text() == "qa\n"


# --- C12: scaffold/verify phases carry a real contract ---------------------


def test_scaffold_prompt_names_contract_and_tasks(tmp_path):
    # The base template's PHASE CONTRACT omits scaffold, so without an appended
    # phase context the worker got a bare phase label. The contract path and
    # the epic's tasks must reach the prompt.
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "r-scaffold")
    captured = {}
    driver._invoke = lambda tid, phase: (
        captured.update(prompt=driver._default_prompt(tid, phase)) or "done"
    )
    rp.run_scaffold(
        driver,
        {"t1": rp.new_task("t1", "add auth"), "t2": rp.new_task("t2", "add profile")},
    )
    prompt = captured["prompt"]
    assert ".mash/parallel/scaffold-contract.md" in prompt
    assert "add auth" in prompt and "add profile" in prompt


def test_verify_prompt_names_role_tip_and_range(tmp_path):
    # The integrated tip was accepted and discarded, so the verifier reviewed
    # nothing in particular. It must now name the role and the exact range.
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "r-verify")
    driver.set_task_context("__verify__/code_review", review_base="base123")
    captured = {}
    driver._invoke = lambda tid, phase: (
        captured.update(tid=tid, prompt=driver._default_prompt(tid, phase)) or "done"
    )
    assert driver.verify_phase("code_review", "tip456") == "done"
    prompt = captured["prompt"]
    assert captured["tid"] == "__verify__/code_review"
    assert "code_review" in prompt
    assert "tip456" in prompt
    assert "base123..tip456" in prompt


def test_parallel_verification_passes_base_to_prompts(tmp_path):
    # run_parallel_verification must hand the review base to the driver so the
    # context lands on the synthetic verify ids.
    driver = rp.HarnessPhaseDriver("pi", tmp_path, "r-verify-base")
    captured = {}
    driver._invoke = lambda tid, phase: (
        captured.update({tid: driver._default_prompt(tid, phase)}) or "done"
    )
    rp.run_parallel_verification(driver, "tip789", base_sha="base000")
    for verifier in ("code_review", "test_runner", "architecture"):
        assert "base000..tip789" in captured[f"__verify__/{verifier}"]


# --- C13: an unconfigured integration gate is reported, not passed ---------


def test_default_gate_reports_not_configured(tmp_path):
    # No suite in the worktree and no explicit command: the run must be able to
    # proceed, but must not claim checks passed.
    ok, failures = rp._default_integration_gate(tmp_path)
    assert ok is True
    assert failures == [rp.GATE_NOT_CONFIGURED]


def test_default_gate_runs_explicit_command(tmp_path):
    ok, failures = rp._default_integration_gate(tmp_path, command="exit 0")
    assert (ok, failures) == (True, [])
    ok2, failures2 = rp._default_integration_gate(
        tmp_path, command="echo boom >&2; exit 3"
    )
    assert ok2 is False
    assert failures2 and "boom" in failures2[0]
