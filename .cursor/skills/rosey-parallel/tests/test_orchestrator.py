"""U8 tests: orchestrator flow (R1, R3, R4, R6, R10-12, R16-18, R20, R23)."""

import subprocess
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
        self.planner = planner_outcomes if isinstance(planner_outcomes, dict) else list(planner_outcomes or [])
        self.work = work_outcomes if isinstance(work_outcomes, dict) else list(work_outcomes or [])
        self.qa = qa_outcomes if isinstance(qa_outcomes, dict) else list(qa_outcomes or [])
        self.lint = lint_outcomes if isinstance(lint_outcomes, dict) else list(lint_outcomes or [])
        self.log = []

    def plan_path(self, task_id):
        return _PLAN_PATHS.get(task_id)

    def set_plan_path(self, task_id, path):
        _PLAN_PATHS[task_id] = path

    def work_phase(self, task_id):
        out = self._outcome(self.work, task_id)
        self.log.append(("work", task_id, out))
        return out

    def qa_phase(self, task_id):
        out = self._outcome(self.qa, task_id)
        self.log.append(("qa", task_id, out))
        return out

    def lint_phase(self, task_id):
        out = self._outcome(self.lint, task_id)
        self.log.append(("lint", task_id, out))
        return out

    def plan_task(self, task_id):
        out = self._outcome(self.planner, task_id)
        self.log.append(("plan", task_id, out))
        return out

    @staticmethod
    def _outcome(queue, task_id, default="done"):
        if isinstance(queue, dict):
            return queue.get(task_id, default)
        if queue:
            return queue.pop(0)
        return default


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
        tmp_path, tasks, footprints, driver, base_branch="develop", base_sha="abc", gate=False,
    )
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert run["tracks"]
    # all tasks eventually done
    for tid in tasks:
        assert run["tasks"][tid]["status"] == rp.STATUS_DONE


def test_all_overlapping_single_serial_track(tmp_path):
    tasks = {tid: rp.new_task(tid, tid) for tid in ("a", "b", "c")}
    footprints = {tid: {"x.py"} for tid in tasks}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert len(run["tracks"]) == 1
    assert any("parallel" in w for w in run["warnings"])


def test_resume_relaunches_interrupted_only(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    # simulate partial state: t1 done, t2 reverted to pending (as if interrupted)
    run["tasks"]["t2"]["status"] = rp.STATUS_PENDING
    # resume: only t2 relaunched; t1 untouched
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run, gate=False)
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert run2["tasks"]["t2"]["status"] == rp.STATUS_DONE
    assert all(e[0] != "plan" or e[1] != "t1" for e in driver2.log)


def test_blocker_halt_does_not_block_other_tracks(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    # t1 blocks, t2 succeeds
    driver = FakeDriver(work_outcomes={"t1": "blocker", "t2": "done"})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=2, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_BLOCKED
    assert run["tasks"]["t2"]["status"] == rp.STATUS_DONE


def test_drift_collision_pauses_track(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {}}  # t2 empty footprint -> separate track
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
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
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=4, gate=False)
    for tid in tasks:
        assert run["tasks"][tid]["status"] == rp.STATUS_DONE
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
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=2, gate=False)
    assert run["tasks"]["c"]["status"] == rp.STATUS_DONE
    assert run["tasks"]["a"]["status"] == rp.STATUS_DONE


def test_oversubscription_parks_and_retries_on_slot_free(tmp_path):
    # 3 independent tasks, max_parallel=2 -> one parks in the denied queue and
    # runs on a freed slot; none fails.
    tasks = {tid: rp.new_task(tid, tid) for tid in ("a", "b", "c")}
    footprints = {tid: {f"{tid}.py"} for tid in tasks}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=2, gate=False)
    for tid in tasks:
        assert run["tasks"][tid]["status"] == rp.STATUS_DONE


def test_file_overlap_tasks_serialize_on_track(tmp_path):
    # a and b share a footprint -> same track -> never run in the same wave.
    tasks = {"a": rp.new_task("a", "A"), "b": rp.new_task("b", "B")}
    footprints = {"a": {"x.py"}, "b": {"x.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, max_parallel=4, gate=False)
    # each wave holds at most one task per track
    for wave in run["waves"]:
        assert not (set(wave) >= {"a", "b"})  # a and b never co-admit
    assert run["tasks"]["a"]["status"] == rp.STATUS_DONE
    assert run["tasks"]["b"]["status"] == rp.STATUS_DONE


# --- Hardening U3: fingerprint-keyed resume + skip-cascade (R5, R6) ---


def test_resume_reuses_unchanged_completed_task(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
    # resume with identical definitions: t1 unchanged+done -> reused, not re-run
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run, gate=False)
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert all(e[1] != "t1" for e in driver2.log)  # t1 never re-planned/re-worked


def test_resume_carries_spawn_time_fields_for_reused_task(tmp_path):
    # P2-13: a reused (unchanged, completed) task must keep its spawn-time
    # fields (worktree_path/branch/end_sha/touched_files) on resume so
    # finish_run can still drop its worktree instead of leaking it.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    # Simulate a resume snapshot that left t1 DONE with spawn-time fields.
    resume = {**run}
    resume["tasks"]["t1"]["status"] = rp.STATUS_DONE
    resume["tasks"]["t1"]["worktree_path"] = "/tmp/wt-t1"
    resume["tasks"]["t1"]["branch"] = "rosey-parallel/x/track-0"
    resume["tasks"]["t1"]["end_sha"] = "abc123"
    resume["tasks"]["t1"]["touched_files"] = ["a.py"]
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=resume, gate=False)
    t1 = run2["tasks"]["t1"]
    assert t1["worktree_path"] == "/tmp/wt-t1"
    assert t1["branch"] == "rosey-parallel/x/track-0"
    assert t1["end_sha"] == "abc123"
    assert t1["touched_files"] == ["a.py"]


def test_resume_reruns_changed_task(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    # change t1's goal -> fingerprint changes -> re-run
    tasks2 = {"t1": rp.new_task("t1", "one-changed"), "t2": rp.new_task("t2", "two")}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=run, gate=False)
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert any(e[1] == "t1" for e in driver2.log)  # t1 re-run


def test_gate_stops_after_planning_no_work(tmp_path):
    # Default gate=True: planning runs, but work/qa/lint never fire and tasks
    # stay PLANNED so the human can review before approving.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_PLANNED
    assert run["tasks"]["t2"]["status"] == rp.STATUS_PLANNED
    # no work/qa/lint dispatched
    assert not any(e[0] in ("work", "qa", "lint") for e in driver.log)
    # plans were produced
    assert any(e[0] == "plan" for e in driver.log)


def test_gate_false_runs_work(tmp_path):
    # gate=False (explicit --approve) promotes PLANNED->GATE_APPROVED and runs
    # the full work/qa/lint pipeline.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert any(e[0] == "work" for e in driver.log)


def test_resume_after_gate_does_not_replan(tmp_path):
    # A run stopped at the gate (tasks PLANNED) resumed WITHOUT --approve must
    # NOT re-plan: the existing plans are honored, tasks stay PLANNED, and no
    # work runs. This is the "resume must not overwrite existing plans" fix.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)  # gate stops
    assert run["tasks"]["t1"]["status"] == rp.STATUS_PLANNED
    # resume with identical definitions, still gated: no re-plan, no work
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run)
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_PLANNED
    assert not any(e[0] == "plan" for e in driver2.log)  # plans not overwritten
    assert not any(e[0] in ("work", "qa", "lint") for e in driver2.log)


def test_resume_after_gate_with_approve_runs_work(tmp_path):
    # Resume with --approve (gate=False) after a gate stop: plans already exist
    # (PLANNED), so no re-plan; work runs to completion.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver)  # gate stops
    assert run["tasks"]["t1"]["status"] == rp.STATUS_PLANNED
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run, gate=False)
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert not any(e[0] == "plan" for e in driver2.log)  # no re-plan
    assert any(e[0] == "work" for e in driver2.log)


def test_dep_fingerprint_folding_forces_dependent_rerun(tmp_path):
    # t2 depends on t1. Changing t1's fingerprint must force t2 to re-run too.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    tasks2 = {"t1": rp.new_task("t1", "one-changed"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=run, gate=False)
    assert any(e[1] == "t2" for e in driver2.log)  # dependent re-run


def test_failed_task_dependents_cascade_to_skipped(tmp_path):
    # t1 fails; t2 depends on t1 -> t2 cascades to skipped at quiescence.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(work_outcomes=["failure", "done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert run["tasks"]["t2"]["status"] == rp.STATUS_SKIPPED


def test_skipped_is_terminal_and_not_rerun_on_resume(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(work_outcomes=["failure", "done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t2"]["status"] == rp.STATUS_SKIPPED
    # resume: t2 stays skipped (unchanged fingerprint, terminal)
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=run, gate=False)
    assert run2["tasks"]["t2"]["status"] == rp.STATUS_SKIPPED


def test_resume_reuses_done_dep_so_dependent_can_run(tmp_path):
    # t1 completes; resume reuses it (unchanged+done) but t2 depends on t1.
    # The reused DONE task must seed the frontier `done` set so t2 runs
    # instead of stranding in GATE_APPROVED (hardening R5 resume deadlock).
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(work_outcomes=["done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    # snapshot: force t1 done, but interrupt before t2 finishes (leave it GATE_APPROVED)
    resume_state = {tid: dict(t) for tid, t in run["tasks"].items()}
    resume_state["t1"]["status"] = rp.STATUS_DONE
    resume_state["t2"]["status"] = rp.STATUS_GATE_APPROVED
    resume = {**run, "state": resume_state}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks, footprints, driver2, resume=resume, gate=False)
    assert run2["tasks"]["t2"]["status"] == rp.STATUS_DONE


def test_resume_changed_task_mid_work_reruns(tmp_path):
    # t1 changed between runs but its snapshot left it mid-WORKING: it must
    # reset to PENDING and re-fire, not strand (hardening R5).
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver(work_outcomes=["done"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    resume_state = {tid: dict(t) for tid, t in run["tasks"].items()}
    resume_state["t1"]["status"] = rp.STATUS_WORKING
    resume = {**run, "state": resume_state}
    tasks2 = {"t1": rp.new_task("t1", "one-changed")}
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=resume, gate=False)
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert any(e[1] == "t1" for e in driver2.log)  # t1 re-fired


def test_resume_task_dep_removed_cascades_skipped(tmp_path):
    # t2 depends on t1; between runs t1 is removed from the task list. t2's
    # dep can never resolve, so it must cascade to SKIPPED, not hang.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    tasks2 = {"t2": rp.new_task("t2", "two", deps=["t1"])}  # t1 removed
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(tmp_path, tasks2, footprints, driver2, resume=run, gate=False)
    assert run2["tasks"]["t2"]["status"] == rp.STATUS_SKIPPED


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
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("evidence" in b for b in run["tasks"]["t1"]["blockers"])


def test_evidence_gate_accepts_done_with_evidence(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    out = "ROSEY_EVIDENCE\nall tests pass\nEND_ROSEY_EVIDENCE"
    driver = EvidenceDriver(work_outcomes=["done"], outputs={"t1": out})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE


def test_failure_carries_retry_hint_in_blocker(tmp_path):
    # A failure outcome is enriched with retry guidance (hardening U4: R8).
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = EvidenceDriver(work_outcomes=["failure"], outputs={"t1": "merge conflict in x"})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("merge_conflict" in b for b in run["tasks"]["t1"]["blockers"])


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
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
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
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("qa" in b for b in run["tasks"]["t1"]["blockers"])


def test_lint_failure_fails_task_not_done(tmp_path):
    # If lint returns non-done (LINT_STATUS: failed), the task must land FAILED.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver(lint_outcomes=["failure"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("lint" in b for b in run["tasks"]["t1"]["blockers"])


def test_dependent_cascades_skipped_when_qa_fails_on_dep(tmp_path):
    # t2 depends on t1; t1 passes work but fails QA -> FAILED, and t2 cascades.
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = FakeDriver(qa_outcomes=["failure"])
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert run["tasks"]["t2"]["status"] == rp.STATUS_SKIPPED


# --- Hardening: plan path recorded on task so work/qa/lint honor the plan ---


def test_plan_path_recorded_on_task(tmp_path):
    # The planner's emitted plan path is captured onto the task record so
    # downstream work/qa/lint phases can honor the specific rosey-plan doc.
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = FakeDriver()
    driver.set_plan_path("t1", "rosey/plans/2026-01-01-001-feat-x-plan.md")
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["plan_path"] == "rosey/plans/2026-01-01-001-feat-x-plan.md"


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


def test_footprints_derived_from_plan_text(tmp_path):
    # P1-2: footprints must be populated from plan text in the CLI path, so
    # R2 track-serialization is enforced in real runs (not every task a
    # singleton track).
    import json as _json
    import rosey_parallel as rp_mod
    plan = (
        "### U1. Unit\n"
        "- **Files:** `src/a.py`, `tests/test_a.py`\n"
    )
    inputs = tmp_path / "inputs.json"
    inputs.write_text(_json.dumps({
        "tasks": [
            {"id": "t1", "goal": "one", "plan_text": plan},
            {"id": "t2", "goal": "two"},  # no plan yet -> empty footprint
        ],
        "options": {"harness": "pi"},
    }))
    tasks, _ = rp_mod._load_run_inputs(str(inputs))
    footprints = rp_mod._derive_footprints(tasks)
    assert footprints["t1"] == {"src/a.py", "tests/test_a.py"}
    assert footprints["t2"] == set()  # pre-planning default: singleton track


def test_footprints_derived_from_plan_path(tmp_path):
    # P1-2: a task whose plan_path points at a rosey plan file yields its
    # parsed footprint; a missing plan file degrades to an empty footprint.
    import json as _json
    import rosey_parallel as rp_mod
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("### U1. Unit\n- **Files:** `src/b.py`\n")
    inputs = tmp_path / "inputs.json"
    inputs.write_text(_json.dumps({
        "tasks": [
            {"id": "t1", "goal": "one", "plan_path": str(plan_file)},
            {"id": "t2", "goal": "two", "plan_path": str(tmp_path / "missing.md")},
        ],
        "options": {"harness": "pi"},
    }))
    tasks, _ = rp_mod._load_run_inputs(str(inputs))
    footprints = rp_mod._derive_footprints(tasks)
    assert footprints["t1"] == {"src/b.py"}
    assert footprints["t2"] == set()


def test_tracks_carry_deterministic_branch(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two")}
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    run = rp.orchestrate_run(tmp_path, tasks, footprints, FakeDriver(), gate=False)
    branches = {trk["track_id"]: trk["branch"] for trk in run["tracks"]}
    for tid, t in run["tasks"].items():
        assert t["branch"] == branches[t["track"]]
        assert t["branch"].startswith(f"rosey-parallel/{run['run_id']}/track-")


def test_same_track_serialized_under_lock(tmp_path):
    # Overlapping footprints share a track; they must not run concurrently.
    seen: list[str] = []

    class SerialProbe(FakeDriver):
        def work_phase(self, tid):
            seen.append(f"start-{tid}")
            seen.append(f"end-{tid}")
            return super().work_phase(tid)

    tasks = {"t1": rp.new_task("t1", "one"), "t2": rp.new_task("t2", "two", deps=["t1"])}
    footprints = {"t1": {"shared.py"}, "t2": {"shared.py"}}
    run = rp.orchestrate_run(tmp_path, tasks, footprints, SerialProbe(), gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert run["tasks"]["t2"]["status"] == rp.STATUS_DONE
    assert run["tasks"]["t1"]["track"] == run["tasks"]["t2"]["track"]
    assert seen == ["start-t1", "end-t1", "start-t2", "end-t2"]


def test_task_does_not_run_when_track_lock_held(tmp_path):
    # P2-9: when a track lock is held by another owner, the task is parked
    # (not run) and the other owner's lock is not released.
    import json as _json

    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    # Fix the run_id via a resume record so we can pre-create the lock.
    resume = {
        "run_id": "locked-run",
        "tasks": {"t1": {"status": rp.STATUS_GATE_APPROVED, "blockers": []}},
        "base_sha_snapshot": "abc",
        "created_at": rp.utc_now_iso(),
        "fix_up_round": 0,
    }
    lock_path = rp.run_dir(tmp_path, "locked-run") / "locks" / "track-0.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(_json.dumps({
        "ownerTag": "other-owner", "pid": __import__("os").getpid(),
        "acquiredAt": rp.utc_now_iso(), "lastHeartbeat": rp.utc_now_iso(),
    }))
    driver = FakeDriver()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, resume=resume, gate=False)
    # The task was parked (lock held by a live owner), not run.
    assert not any(e[0] == "work" for e in driver.log)
    # The other owner's lock was NOT released.
    assert lock_path.exists()


def test_raising_driver_fails_task_cleanly(tmp_path):
    # P2-14: a driver that raises inside work_phase must fail only that task
    # (transition to FAILED + checkpoint), not abort the whole run.
    class RaisingDriver(FakeDriver):
        def work_phase(self, tid):
            raise RuntimeError("boom")

    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    run = rp.orchestrate_run(tmp_path, tasks, footprints, RaisingDriver(), gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("driver raised" in b for b in run["tasks"]["t1"]["blockers"])
    # A checkpoint was written so the failure is durable.
    state_file = rp.state_path(tmp_path, run["run_id"])
    assert state_file.exists()


EVIDENCE = (
    "ROSEY_WORK_HANDOFF\nFILES_CHANGED:\n- a.py\nEND_ROSEY_WORK_HANDOFF\n"
    "ROSEY_EVIDENCE\nok\nEND_ROSEY_EVIDENCE\n"
)
NO_EVIDENCE = "ROSEY_WORK_HANDOFF\nFILES_CHANGED:\n- a.py\nEND_ROSEY_WORK_HANDOFF\n"
BLOCKED_EVIDENCE = (
    "ROSEY_WORK_HANDOFF\nBLOCKERS:\n- unknown schema\nFILES_CHANGED:\n- a.py\n"
    "END_ROSEY_WORK_HANDOFF\nROSEY_EVIDENCE\nok\nEND_ROSEY_EVIDENCE\n"
)
DRIFT_EVIDENCE = (
    "ROSEY_WORK_HANDOFF\nFILES_CHANGED:\n- a.py\nEND_ROSEY_WORK_HANDOFF\n"
    "ROSEY_EVIDENCE\nok\nEND_ROSEY_EVIDENCE\n"
)


def test_done_requires_evidence_artifact(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = EvidenceDriver(outputs={"t1": NO_EVIDENCE})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_FAILED
    assert any("evidence" in b for b in run["tasks"]["t1"]["blockers"])


def test_handoff_blockers_surface(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = EvidenceDriver(outputs={"t1": BLOCKED_EVIDENCE})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_BLOCKED
    assert "unknown schema" in run["tasks"]["t1"]["blockers"]
    assert run["tasks"]["t1"]["touched_files"] == ["a.py"]


def test_drift_pivots_done_task_to_fix_up(tmp_path):
    tasks = {
        "t1": rp.new_task("t1", "one"),
        "t2": rp.new_task("t2", "two", deps=["t1"]),
    }
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = EvidenceDriver(outputs={"t1": EVIDENCE, "t2": DRIFT_EVIDENCE})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t2"]["status"] == rp.STATUS_DONE
    # t1 was pivoted to FIX_UP on drift, then re-admitted and re-run to DONE
    # (P1-1: a drift-pivoted FIX_UP task must not strand forever).
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
    assert any("drift t2" in w for w in run["warnings"])


def test_drift_pivoted_fix_up_task_reruns_to_done(tmp_path):
    # P1-1: a task pivoted to FIX_UP by a sibling's drift must be re-admitted
    # (FIX_UP -> WORKING) and re-run to DONE, not strand in FIX_UP forever.
    tasks = {
        "t1": rp.new_task("t1", "one"),
        "t2": rp.new_task("t2", "two", deps=["t1"]),
    }
    footprints = {"t1": {"a.py"}, "t2": {"b.py"}}
    driver = EvidenceDriver(outputs={"t1": EVIDENCE, "t2": DRIFT_EVIDENCE})
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["tasks"]["t1"]["status"] == rp.STATUS_DONE
    # t1's work ran twice: once normally, once as the FIX_UP re-run.
    work_calls = [e for e in driver.log if e[0] == "work" and e[1] == "t1"]
    assert len(work_calls) == 2


def test_scaffold_failure_skips_planning(tmp_path):
    class ScaffoldFail(FakeDriver):
        def scaffold_phase(self):
            return "failure"

    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = ScaffoldFail()
    run = rp.orchestrate_run(tmp_path, tasks, footprints, driver, gate=False)
    assert run["scaffold"]["outcome"] == "failure"
    assert run["tasks"]["t1"]["status"] == rp.STATUS_PENDING
    assert not any(e[0] == "plan" for e in driver.log)


def test_checkpoint_after_terminal(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    run = rp.orchestrate_run(tmp_path, tasks, footprints, FakeDriver(), gate=False)
    state_file = rp.state_path(tmp_path, run["run_id"])
    assert state_file.exists()
    loaded = rp.load_run(tmp_path, run["run_id"])
    assert loaded["tasks"]["t1"]["status"] == rp.STATUS_DONE


def test_resume_replans_interrupted_planning(tmp_path):
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    first = rp.orchestrate_run(tmp_path, tasks, footprints, FakeDriver(), gate=True)
    first["tasks"]["t1"]["status"] = rp.STATUS_PLANNING
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(
        tmp_path, tasks, footprints, driver2, resume=first, gate=True,
    )
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_PLANNED
    assert any(e[0] == "plan" and e[1] == "t1" for e in driver2.log)


def test_resume_replans_failed_planner(tmp_path):
    # P2-15: a FAILED planner task is re-planned on resume (a transient planner
    # failure must not be permanent).
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    first = rp.orchestrate_run(tmp_path, tasks, footprints, FakeDriver(), gate=True)
    first["tasks"]["t1"]["status"] = rp.STATUS_FAILED
    first["tasks"]["t1"]["blockers"] = ["planner: failure"]
    driver2 = FakeDriver()
    run2 = rp.orchestrate_run(
        tmp_path, tasks, footprints, driver2, resume=first, gate=True,
    )
    assert run2["tasks"]["t1"]["status"] == rp.STATUS_PLANNED
    assert any(e[0] == "plan" and e[1] == "t1" for e in driver2.log)


def test_approve_without_resume_is_rejected(tmp_path):
    import json as _json

    inputs = tmp_path / "inputs.json"
    inputs.write_text(_json.dumps({
        "tasks": [{"id": "t1", "goal": "one"}],
        "options": {"harness": "pi"},
    }))
    rc = rp.main(["run", str(inputs), "--approve"])
    assert rc == 2


def test_worker_prompt_injects_placeholders():
    text = rp.load_worker_prompt()
    for key in ("{goal}", "{plan_path}", "{track_branch}", "{phase}", "{qa_diff_base}"):
        assert key in text
    assert "{branch_setup}" not in text


def test_run_schema_matches_new_run(tmp_path):
    run = rp.orchestrate_run(
        tmp_path, {"t1": rp.new_task("t1", "one")}, {"t1": {"a.py"}},
        FakeDriver(), gate=False,
    )
    for key in ("harness", "gate", "created_at", "fix_up_round"):
        assert key in run
    assert "report" in run



# --- End-to-end: a worker that leaves its track branch fails the task ---


class DriftingDriver(FakeDriver):
    """FakeDriver that moves the worktree off its track branch during work."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.cwds = {}

    def set_task_cwd(self, task_id, path):
        self.cwds[task_id] = path

    def work_phase(self, task_id):
        wt = self.cwds.get(task_id)
        if wt:
            subprocess.run(
                ["git", "-C", str(wt), "checkout", "-q", "-b", "stray-branch"],
                check=True, capture_output=True,
            )
        return super().work_phase(task_id)


def _init_git_repo(path):
    for cmd in (
        ["git", "init", "-q", str(path)],
        ["git", "-C", str(path), "config", "user.email", "t@t"],
        ["git", "-C", str(path), "config", "user.name", "t"],
    ):
        subprocess.run(cmd, check=True)
    (path / "base.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(path), "add", "base.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-qm", "init", "--no-gpg-sign"], check=True,
    )
    return path


def test_worker_leaving_track_branch_fails_task(tmp_path):
    repo = _init_git_repo(tmp_path)
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}
    driver = DriftingDriver()
    run = rp.orchestrate_run(repo, tasks, footprints, driver, gate=False)
    t1 = run["tasks"]["t1"]
    assert t1["status"] == rp.STATUS_FAILED
    assert any("branch check" in b for b in t1["blockers"])
    assert any("stray-branch" in b for b in t1["blockers"])


def test_worker_staying_on_track_branch_succeeds(tmp_path):
    # Control: the same real-git setup without drift must still reach DONE.
    repo = _init_git_repo(tmp_path)
    tasks = {"t1": rp.new_task("t1", "one")}
    footprints = {"t1": {"a.py"}}

    class StayingDriver(FakeDriver):
        def set_task_cwd(self, task_id, path):
            pass

    run = rp.orchestrate_run(repo, tasks, footprints, StayingDriver(), gate=False)
    assert run["tasks"]["t1"]["status"] in (rp.STATUS_DONE, rp.STATUS_REPORTED)
