# Handoff

Read this when Phase 2 completes. It owns the lint gate, the Sentrux handoff gate, the review brief, Hindsight retain, the handoff envelope, and the evidence artifact.

## Phase 3: Handoff

Entered when all Phase 2 tasks are complete.

1. **Run `rosey-lint` before handoff**:
   - Load [`rosey-lint`](../../rosey-lint/SKILL.md).
   - Run its discovery and execution pipeline for format, lint, type-check, and build commands available in the current repository. In non-interactive mode, invoke it with `mode:non-interactive`.
   - **Read the `LINT_HANDOFF` block it returns.** `rosey-lint` emits `LINT_HANDOFF ... END_LINT_HANDOFF` with per-step results and `LINT_STATUS: pass|failed` — that block is the authoritative outcome, not prose in the transcript. In interactive mode, request the block when it was not emitted.
   - Carry each `STEPS:` line into the handoff envelope's `VERIFY:` list (for example `lint: pass`, `build: skipped`).
   - If `rosey-lint` applies fixes, update `FILES_CHANGED` with every file it created or modified.
   - On `LINT_STATUS: failed`, stop and report the failing command and relevant output. Do not prepare success handoff context until lint/build verification passes or, in interactive mode only, the user explicitly decides to proceed. **When the user overrides a failure, record it as `lint: failed (user override: <reason>)` in `VERIFY:`** — a proceeded-anyway failure must never read as a pass downstream.

2. **Run the plan's Verification Contract**, when the plan carries one. These are the repo's own commands and quality gates; run them alongside `rosey-lint` and carry both into `VERIFY:`. There is no precedence question between this and the per-unit `Verification` fields — those are the done signal for a single task inside the Phase 2 loop, these are plan-wide and run here. When the plan has no Verification Contract (or there is no plan at all), note the gap in the envelope and rely on `rosey-lint` plus the per-unit checks.
3. **Run the Sentrux handoff gate** when Sentrux is available:
   - Call MCP `session_end`.
   - Call MCP `test_gaps`.
   - Compare the session result against the baseline.
   - If `session_end` fails, attempt focused remediation for structural regressions, then rerun `session_end`.
   - If it still fails, stop and report the block. Continue only in interactive mode if the user gives the exact override phrase from `rosey-sentrux`: `override sentrux handoff block`. In non-interactive mode, do not wait for an override.
4. **Write the review brief** beside the plan as `<plan-basename>.sentrux-review-brief.json`.
   - Include session pass/fail, signal before/after, bottleneck after, `test_gaps`, unavailable reason if applicable, and override details if used.
5. **Retain Hindsight session memory** when Hindsight is available:
   - Use [`rosey-hindsight`](../../rosey-hindsight/SKILL.md) to retain a concise but rich summary with plan path, changed files, completed work, verification commands, blockers, and important decisions.
   - If Hindsight is unavailable or not configured, skip retain and record the status in the handoff envelope.
6. **Prepare handoff context**:
   - Emit a compact, stable envelope. Keep the field names below so later skills (`rosey-qa`, `rosey-pr` — both invoked explicitly) can consume the handoff without parsing prose:

     ```text
     ROSEY_WORK_HANDOFF
     BRANCH: <current branch — work happens in place; no branch setup>
     FILES_CHANGED:
     - <repo-relative path>
     DONE:
     - <U-ID or task>: <completed change, <=12 words>
     WHAT_WAS_IMPLEMENTED:
     <1-3 terse lines summarizing completed Implementation Units>
     PLAN_OR_REQUIREMENTS: <plan path plus origin requirements path when present>
     VERIFY:
     - <command or gate>: <pass | failed | skipped with reason>
     BLOCKERS: <none | one-line blocker>
     HINDSIGHT: <available | unavailable | skipped> -- <brief reason>
     SENTRUX: <pass | failed | unavailable | override> -- <brief reason>
     SENTRUX_REVIEW_CONTEXT:
     <compact markdown summary from the review brief, or unavailable reason>
     END_ROSEY_WORK_HANDOFF
     ```

   - `BRANCH`, `FILES_CHANGED`, `WHAT_WAS_IMPLEMENTED`, `PLAN_OR_REQUIREMENTS`, and `SENTRUX_REVIEW_CONTEXT` are required for downstream compatibility.
   - `DONE`, `VERIFY`, `BLOCKERS`, `HINDSIGHT`, and `SENTRUX` are compact machine-to-machine fields. Keep each line short; put full detail in artifacts or blocker reports only when needed.

7. **Run the final checks before the envelope goes out:**
   - All tasks marked completed
   - **Check the plan's Definition of Done, including its cleanup criterion** — a long run accumulates dead-end and experimental code from approaches that did not pan out, and declaring done requires removing it, not leaving it in the diff. This is distinct from Phase 2's "Simplify as You Go", which consolidates _kept_ code; this removes _abandoned_ code
   - Every requirement the plan traces is satisfied, and any `Deferred to Implementation` question was resolved during execution
   - Files this run deliberately left uncommitted (pre-work WIP collisions) are named, so `rosey-pr` does not publish them silently
8. **Emit the evidence artifact** immediately after the envelope (required):

   ```text
   ROSEY_EVIDENCE
   <captured verification output proving the work — test run summary, lint/build
   result, or the command output that satisfied the plan's Verification criteria>
   END_ROSEY_EVIDENCE
   ```

   The body must be non-empty. [`rosey-parallel`](../../rosey-parallel/SKILL.md) treats a missing or empty block as task failure even when the handoff envelope is well-formed — a run is not done without proof it was verified.

   **Name the command, then paste its real output — not a summary of it.** "Tests pass" is not evidence; `make test` followed by the relevant output tail is. When the repository has no Make target, use the Compose fallback. When no automated verification was possible (no configured test runner, manual-only surface), state that explicitly along with whatever check _was_ run; do not omit the block.

9. **Stop**. Do not invoke `rosey-qa`, `rosey-pr`, or any shipping workflow. Shipping/QA adaptation is handled by a separate plan.
