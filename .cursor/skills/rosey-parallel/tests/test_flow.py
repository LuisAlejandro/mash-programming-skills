"""Hardening U5 tests: flow shape — scaffold phase + parallel verification (R9, R10)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402


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


def test_parallel_verification_consumes_integrated_tip():
    driver = FakeFlowDriver()
    rp.run_parallel_verification(driver, "integrated-tip-sha")
    assert all(e[2] == "integrated-tip-sha" for e in driver.log)
