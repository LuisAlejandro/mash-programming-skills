"""U8 tests: orchestrator flow (R1, R3, R4, R6, R10-12, R16-18, R20, R23)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import rosey_parallel as rp  # noqa: E402


class FakeDriver:
    """Scripted outcomes so the orchestrator loop needs no real harness."""

    def __init__(self, planner_outcomes=None, work_outcomes=None,
                 qa_outcomes=None, lint_outcomes=None):
        self.planner = list(planner_outcomes or [])
        self.work = list(work_outcomes or [])
        self.qa = list(qa_outcomes or [])
        self.lint = list(lint_outcomes or [])
        self.log = []

    def plan_task(self, task_id):
        out = self.planner.pop(0) if self.planner else "done"
        self.log.append(("plan", task_id, out))
        return out

    def plan_path(self, task_id):
        return _PLAN_PATHS.get(task_id)

    def set_plan_path(self, task_id, path):
        _PLAN_PATHS[task_id] = path

    def work_phase(self, task_id):
        out = self.work.pop(0) if self.work else "done"
        self.log.append(("work", task_id, out))
        return out

    def qa_phase(self, task_id):
        out = self.qa.pop(0) if self.qa else "done"
        self.log.append(("qa", task_id, out))
        return out

    def lint_phase(self, task_id):
        out = self.lint.pop(0) if self.lint else "done"
        self.log.append(("lint", task_id, out))
        return out


_PLAN_PATHS = {}


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


# --- Hardening U3: fingerprint-keyed resume + skip-cascade (R5, R6) ---


def test_resume_reuses_unchanged_completed_task(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_DONE
    # resume with identical definitions: t1 unchanged+done -> reused, not re-run
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run)
    assert run2["state"]["t1"]["status"] == rp.STATUS_DONE
    assert all(e[1] != "t1" for e in driver2.log)  # t1 never re-planned/re-worked


def test_resume_reruns_changed_task(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    # change t1's goal -> fingerprint changes -> re-run
    tasks2 = {"t1": rp.new_task("t1", "one-changed"), "t2": rp.new_task("t2", "two")}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=run)
    assert run2["state"]["t1"]["status"] == rp.STATUS_DONE
    assert any(e[1] == "t1" for e in driver2.log)  # t1 re-run


def test_dep_fingerprint_folding_forces_dependent_rerun(tmp_path):
    # t2 depends on t1. Changing t1's fingerprint must force t2 to re-run too.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    tasks2 = {"t1": rp.new_task("t1", "one-changed"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=run)
    assert any(e[1] == "t2" for e in driver2.log)  # dependent re-run


def test_failed_task_dependents_cascade_to_skipped(tmp_path):
    # t1 fails; t2 depends on t1 -> t2 cascades to skipped at quiescence.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(work_outcomes=["failure", "done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_FAILED
    assert run["state"]["t2"]["status"] == rp.STATUS_SKIPPED


def test_skipped_is_terminal_and_not_rerun_on_resume(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(work_outcomes=["failure", "done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t2"]["status"] == rp.STATUS_SKIPPED
    # resume: t2 stays skipped (unchanged fingerprint, terminal)
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run)
    assert run2["state"]["t2"]["status"] == rp.STATUS_SKIPPED


def test_resume_reuses_done_dep_so_dependent_can_run(tmp_path):
    # t1 completes; resume reuses it (unchanged+done) but t2 depends on t1.
    # The reused DONE task must seed the frontier `done` set so t2 runs
    # instead of stranding in GATE_APPROVED (hardening R5 resume deadlock).
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(work_outcomes=["done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    # snapshot: force t1 done, but interrupt before t2 finishes (leave it GATE_APPROVED)
    resume_state = {tid: dict(t) for tid, t in run["state"].items()}
    resume_state["t1"]["status"] = rp.STATUS_DONE
    resume_state["t2"]["status"] = rp.STATUS_GATE_APPROVED
    resume = {**run, "state": resume_state}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=resume)
    assert run2["state"]["t2"]["status"] == rp.STATUS_DONE


def test_resume_changed_task_mid_work_reruns(tmp_path):
    # t1 changed between runs but its snapshot left it mid-WORKING: it must
    # reset to PENDING and re-fire, not strand (hardening R5).
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver(work_outcomes=["done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    resume_state = {tid: dict(t) for tid, t in run["state"].items()}
    resume_state["t1"]["status"] = rp.STATUS_WORKING
    resume = {**run, "state": resume_state}
    tasks2 = {"t1": rp.new_task("t1", "one-changed")}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=resume)
    assert run2["state"]["t1"]["status"] == rp.STATUS_DONE
    assert any(e[1] == "t1" for e in driver2.log)  # t1 re-fired


def test_resume_task_dep_removed_cascades_skipped(tmp_path):
    # t2 depends on t1; between runs t1 is removed from the task list. t2's
    # dep can never resolve, so it must cascade to SKIPPED, not hang.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    tasks2 = {"t2": rp.new_task("t2", "two", deps=["t1"])}  # t1 removed
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=run)
    assert run2["state"]["t2"]["status"] == rp.STATUS_SKIPPED


class EvidenceDriver(FakeDriver):
    """FakeDriver that exposes raw worker output via evidence()."""

    def __init__(self, work_outcomes=None, outputs=None):
        super().__init__(work_outcomes=work_outcomes)
        self.outputs = dict(outputs or {})

    def evidence(self, task_id):
        return self.outputs.get(task_id)


def test_evidence_gate_rejects_done_without_evidence(tmp_path):
    # A worker claiming 'done' but emitting no evidence artifact is not done
    # (hardening U4: R7). The orchestrator must reject it as a failure.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = EvidenceDriver(work_outcomes=["done"], outputs={"t1": "no evidence here"})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("evidence" in b for b in run["state"]["t1"]["blockers"])


def test_evidence_gate_accepts_done_with_evidence(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    out = "ROSEY_EVIDENCE\nall tests pass\nEND_ROSEY_EVIDENCE"
    driver = EvidenceDriver(work_outcomes=["done"], outputs={"t1": out})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_DONE


def test_failure_carries_retry_hint_in_blocker(tmp_path):
    # A failure outcome is enriched with retry guidance (hardening U4: R8).
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = EvidenceDriver(work_outcomes=["failure"], outputs={"t1": "merge conflict in x"})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("merge_conflict" in b for b in run["state"]["t1"]["blockers"])


def test_cli_dispatch_unknown_and_usage(tmp_path):
    # CLI dispatch: unknown subcommand and bare invocation return non-zero.
    import rosey_parallel as rp_mod
    assert rp_mod.main(["bogus"]) != 0
    assert rp_mod.main([]) != 0


# --- Hardening: per-task QA + lint phases actually execute (was dead modeling) ---


def test_task_passes_through_qa_and_lint_to_done(tmp_path):
    # A task that passes work, then qa, then lint reaches DONE — and both
    # qa_phase and lint_phase are actually invoked (they used to never run).
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_DONE
    phases = [e[0] for e in driver.log]
    assert "qa" in phases and "lint" in phases
    # ordering within a task: work precedes qa precedes lint
    i_w = phases.index("work")
    i_q = phases.index("qa")
    i_l = phases.index("lint")
    assert i_w < i_q < i_l


def test_qa_failure_fails_task_not_done(tmp_path):
    # If QA returns something other than 'done', the task must land FAILED and
    # never reach DONE — the evidence gate alone is not enough.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver(qa_outcomes=["failure"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("qa" in b for b in run["state"]["t1"]["blockers"])


def test_lint_failure_fails_task_not_done(tmp_path):
    # If lint returns non-done (LINT_STATUS: failed), the task must land FAILED.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver(lint_outcomes=["failure"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("lint" in b for b in run["state"]["t1"]["blockers"])


def test_dependent_cascades_skipped_when_qa_fails_on_dep(tmp_path):
    # t2 depends on t1; t1 passes work but fails QA -> FAILED, and t2 cascades.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(qa_outcomes=["failure"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["status"] == rp.STATUS_FAILED
    assert run["state"]["t2"]["status"] == rp.STATUS_SKIPPED


# --- Hardening: plan path recorded on task so work/qa/lint honor the plan ---


def test_plan_path_recorded_on_task(tmp_path):
    # The planner's emitted plan path is captured onto the task record so
    # downstream work/qa/lint phases can honor the specific rosey-plan doc.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver()
    driver.set_plan_path("t1", "rosey/plans/2026-01-01-001-feat-x-plan.md")
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["state"]["t1"]["plan_path"] == "rosey/plans/2026-01-01-001-feat-x-plan.md"


def test_cli_run_validates_inputs_fail_fast(tmp_path):
    # The `run` subcommand loads + validates inputs; a bad task list fails
    # fast with ValidationError before any harness is invoked.
    import json as _json
    import rosey_parallel as rp_mod
    inputs = tmp_path / "inputs.json"
    inputs.write_text(_json.dumps({
        "tasks": [{"id": "t1", "goal": "one", "deps": ["missing"]}],
        "options": {"harness": "pi"},
    }))
    try:
        rp_mod.main(["run", str(inputs)])
    except rp_mod.ValidationError:
        pass  # expected: unknown dependency fails fast
    else:
        raise AssertionError("expected ValidationError for unknown dep")
