# Dogfood phases 0–5

Required read before Phase 0. Full detail for every phase; the skill body carries the outcome, the boundaries, the phase order, and the terminal states.

## Phase 0: Intake and resume

Parse `$ARGUMENTS` as `SKILL.md` specifies. Then read `references/intake.md` and follow it — it owns owner/repo, window vs explicit PRs, GitHub MCP fetch, empty-set handling, and resume.

Optional Hindsight recall after the window slug is known: test-account prefs, known flaky flows, prior dogfood outcomes. Continue if the daemon is down.

Do not switch branches. Do not create a worktree.

## Phase 1: Extract and cluster

Read `references/scope-extraction.md` and follow it. That file owns skip rules, union, clustering, adjacent regression, and persona grounding.

Announce the clusters and the skip table before mapping flows. This is progress, not a blocking confirm.

If every PR was skipped, still continue to Phase 2 with zero clusters so the report exists.

## Phase 2: Map flows, build the matrix, confirm

Do not jump to a flat list of pages. Understand the journeys the clusters touch, then derive the matrix from them.

### 2a. Map the user flows

For every cluster, trace the complete journey end to end and draw it. Map each flow as a **Mermaid `flowchart`**: entry point, each user action, branch points (success / validation error / empty / permission-denied), side effects (emails, jobs, notifications), and the true end state.

Produce one flowchart per distinct journey, scaled to the window: a copy-only cluster gets a small chart; a multi-step feature gets several. Cover the happy path **and** the branch points. Mapping is never skipped — these diagrams ARE the understanding; they become the spine of the matrix and belong in the report.

Read `references/test-matrix-taxonomy.md` for non-page surfaces (API, agent tool, email) so a cluster without a route still gets a flowchart or an explicit skip/block reason.

### 2b. Derive the matrix from the flows

Walk each flowchart and turn every node and branch into one or more test scenarios using the taxonomy (journeys, functional, experiential, empty/error/boundary, a11y, responsive, adjacent regression, non-page).

Attach originating PR numbers to each row. Adjacent-regression rows may omit PRs.

**Load the matrix as a task list** (the harness's task tool), one task per scenario, ordered by flow, not by PR.

**Create the report now.** Read `references/report-template.md` and instantiate it at `<repo-root>/.mash/dogfood/<YYYY-MM-DD>-<window-slug>.md` with every scenario at `Pending`. Fill Window & intake, Out of scope, Personas, and Flows. The checkpoint must be template-shaped, not a bare table.

### 2c. Confirm the matrix

**Interactive:** show the clustered journeys, the skip table, and the matrix. Ask one question: proceed as written / drop a named journey / add a missing journey. Apply the answer, then update the report. Do not start the browser until this question returns.

**Non-interactive:** skip the question. Set **Matrix confirm** to `unreviewed` in the report and continue.

A zero-row matrix (nothing user-visible shipped) skips serve and execute. Finalize the report with an empty matrix and a "nothing to drive" verdict.

## Phase 3: Serve

Read `references/serve.md` and follow it. That file owns Make/Compose discovery, port reuse, staging/prod URLs, and prod safety.

Do not open the browser until the base URL accepts connections (local) or is known (staging/prod).

## Phase 4: Execute the matrix

Read `references/browser.md` before the first navigation. Work the task list **one item at a time**. For each scenario, mark the task `in_progress`, then:

1. **Document** the journey and the expected outcome.
2. **Drive it** through the browser contract in `references/browser.md` to the true end state.
3. **Judge** correctness and experience: right data, right destination, sensible content, no console errors, aligned with the product.
4. **Walk it as each persona.** Paper cuts do not block a `Pass`. Record them in the report. v1 defers every paper cut — do not edit product code.
5. **Record** `Pass`, `Fail`, `Skipped`, or `Blocked (needs human verify)` in the matrix. Update the report after the judgment. Mark the task `completed` only when the status is no longer `Pending`.

**Fail** is a functional miss. Capture symptom, expected vs actual, and evidence in the Failures section. Do not implement a fix.

**External-interaction and prod-mutation legs** cannot be fully driven: mark `Blocked (needs human verify)`, continue the rest of the matrix, and never silently re-queue them.

A sharp paper cut is still deferred in v1. If it is severe enough to be a defect, also add a `Fail` on a dedicated scenario or a Decisions-for-a-human block — do not edit CSS on `main`.

## Phase 5: Finalize

When every scenario is `Pass`, `Fail`, `Skipped`, or `Blocked (needs human verify)`, finalize against `references/report-template.md`. Confirm every template-owned section is present. Do not reconstruct the section list from memory.

Surface a short chat summary: verdict, fail count, blocked items, report path.

Then read `references/handoff.md` and follow it. Interactive runs with at least one `Fail` offer to file GitHub issues. Non-interactive runs skip the offer. Never commit, push, or open a PR from this skill.
