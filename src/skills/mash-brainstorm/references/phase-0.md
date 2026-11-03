# Phase 0: Communication, Memory Gate, Resume, Classify, and Scope

Read this before anything else on every run. It carries the memory gate as well as Phase 0 itself.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule. Do not restate them here.

## Phase 0: Resume, Assess, and Route

**Memory gate (hard):** Run this **before any Phase 0 subsection** — before 0.0, resume, classification, or the Phase 1.1 grounding scout. Do not search the repo or dispatch research until the gate completes.

1. Read [`mash-hindsight`](../../mash-hindsight/SKILL.md), run its availability check (daemon status **and** the `/version` fingerprint), then `memory recall`; OR document `Hindsight: unavailable (<reason>)`. The skill owns the procedure — do not restate it.
2. First status line: `Hindsight: recalled (<brief useful context>)` or `Hindsight: unavailable (<reason>)`. Envelope field `HINDSIGHT:` stays separate.
3. Do not write the requirements doc until step 1 completes or is explicitly marked unavailable.

"Unavailable" means CLI failed — not "I skipped it."

### 0.0 Markdown Output

Requirements documents are always markdown (`.md`). Read `references/markdown-rendering.md` for format principles, paired with `references/brainstorm-sections.md` for section content.

When `mode:non-interactive` is active, apply Compact non-interactive artifacts from Output Guidance in `references/interaction-rules.md`: preserve IDs and decision-bearing content, trim narrative.

**Token-parsing convention:** only literal-prefix flag tokens (`mode:`) are consumed and stripped. Other `<word>:<word>` tokens — including conventional commit prefixes like `feat:`, `fix:`, `chore:` that may appear inside a feature description — pass through verbatim.

### 0.1 Resume Existing Work When Appropriate

If the user references an existing brainstorm topic or document, or there is an obvious recent matching `*-requirements.md` file in the **flat** `.mash/brainstorms/` directory:

- Search the primary checkout's flat `.mash/brainstorms/` and each flat `.mash/worktrees/<slug>/.mash/brainstorms/` for a software run. Never `.mash/brainstorms/scratch/` (per-run scout artifacts). Never `.mash/parallel/` — it is not a search root.
- Read the document
- Confirm with the user before resuming: "Found an existing requirements doc for [topic]. Should I continue from this, or start fresh?"
- If resuming, summarize the current state briefly, continue from its existing decisions and outstanding questions, and update the existing document instead of creating a duplicate

In non-interactive mode, do not ask. Resume the matching document when the topic match is unambiguous; otherwise start fresh and record the choice as an assumption.

### 0.1b Classify Task Domain

Before proceeding to Phase 0.2, classify whether this is a software task. The key question is: **does the task involve building, modifying, or architecting software?** -- not whether the task *mentions* software topics.

**Software** (continue to Phase 0.2) -- the user asks to build, modify, refactor, debug, architect, or deploy software. Always write `*-requirements.md`. A request that merely *references* code, a repo, an API, or a database is not software by itself.

**Non-software** -- BOTH conditions must be true:

- The user is not asking to build, modify, refactor, debug, architect, or deploy software
- The task describes something the user wants to explore, decide, or think through in a non-software domain

Stop. Say that mash-brainstorm covers software work and this request does not. Do not write a requirements file.

**Neither** (not a brainstorm run) -- the input is a quick-help request, error message, factual question, or single-step task that doesn't need a brainstorm. Answer and stop; skip all brainstorming phases.

### 0.2 Assess Whether Brainstorming Is Needed

**Clear requirements indicators:**

- Specific acceptance criteria provided
- Referenced existing patterns to follow
- Described exact expected behavior
- Constrained, well-defined scope

**If requirements are already clear:** Skip Phase 1.1 and 1.2. If one direction is already settled, skip Phase 2 and write the requirements document. If more than one plausible direction remains, do Phase 2, then write. The confirmation is the written file, in Phase 3.

### 0.3 Scope floor

Work too small for a requirements document does not belong in this skill — see the scope floor in `SKILL.md`. If it is unclear whether the work is large enough, ask one targeted question and then proceed. When it stays uncertain, stay in the skill and write the requirements document.

In non-interactive mode, do not ask. A software request that reached this skill writes a requirements document.

**Every software run writes a requirements document.** `mash-plan` requires it as origin. There is no software-route chat-only outcome.

**Gates (do not run scout / approaches / verifier on every run):**
- Clear-requirements (0.2) skips Phase 1.1 and 1.2.
- The Phase 1.1 grounding scout runs only when Phase 1.1 runs.
- Approach generation follows the gates in `references/approaches.md`.
- The claim verifier runs only for checkable repo claims (see `references/approaches.md`).

**Coherent-work gate.** Before entering Phase 1, check whether the request contains more than one independently plannable product outcome: each has its own user value or acceptance boundary and could be delivered without completing the others. Shared actors, one end-to-end outcome, or coverage across named devices, providers, or data sources do not by themselves justify a split — that is Core Principle 7.

When the gate finds multiple coherent areas:

1. Propose a plain-language breakdown and state only relationships supported now: which areas depend on or enable others, share a product rule, or can proceed independently.
2. Ask which one area this brainstorm should own. If the user already chose one, carry it forward instead of asking again.
3. Treat that area as the sole source of Requirements, Flows, Acceptance Examples, and Key Decisions. Other areas remain contextual candidates, not scope.
4. Preserve the current broader understanding for a **How This Work Fits Together** section in the requirements document. Mark tentative relationships as tentative; later brainstorms may revise, split, merge, or discard them.
5. Carry the boundary into the Summary: name the current area and state that the surrounding areas are not active scope.

Keep the work together when the outcomes cannot be independently useful or validated, or when separating them would force this document to invent the missing shared behavior. This gate narrows the active artifact; it does not create a parent plan or a roadmap, and it never routes to another skill.

In non-interactive mode, do not ask. Choose the area the feature description weights most heavily, record the narrowing as an explicit assumption, and note the deferred areas under Scope Boundaries.

**Unfamiliarity tripwire.** If the user signals they lack working knowledge of the domain or the territory the topic touches — "I know nothing about X", "never touched the auth modules", "I don't know what's possible / what I should be asking" — read `references/blindspot-pass.md` now. Loading here is readiness only; that reference owns when the offer fires (territory-scoped, before the first substantive question into the flagged territory), the map's shape, and how mapped decisions re-enter the dialogue. Skip the tripwire entirely in non-interactive mode — with no user to teach, flagged territory is handled as a declined offer per that reference.

### 0.4 Feature Worktree (software runs)

Runs after 0.1b classifies the task as software and before Phase 1. Non-software and "neither" runs stop earlier, so they never create a worktree.

1. **Slug.** Use the brainstorm's `topic` (kebab-case, `^[a-z0-9][a-z0-9-]{0,63}$`). When resuming, reuse the document's `topic`.
2. **Register the run, then create its worktree.** A worktree belongs to a run, never to a slug: two brainstorms on the same topic must not be handed the same directory.

   ```bash
   RUN=$(python3 "<skills>/mash-workspace/scripts/workspace.py" run start \
         --workflow brainstorm --repo <repo-root> \
         | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
   python3 scripts/feature_worktree.py create <slug> --run "$RUN" --repo <repo-root>
   ```

   Run the second command from this skill's directory. It creates `feature/<slug>-<run-suffix>` at `.mash/worktrees/<slug>-<run-suffix>` from the primary checkout's `HEAD`, copies the runtime allowlist, and holds the `workspace` lease. `status` is `created`. A repeated slug in a different run gets a different directory; if the same run retries, it is refused and the recorded path from the run record is resumed instead.
3. **Record the absolute worktree path.** Every read and write of `.mash/` for this run uses that root: scratch, the requirements document, and the Phase 4 handoff. Document content stays repo-relative.
4. **Resumed document in the primary checkout.** Copy it into the worktree's flat `.mash/brainstorms/` under the same name when the worktree does not already have it. Update the worktree copy, never the primary one.
5. **Uncommitted changes stay in the primary checkout.** The new branch starts from committed `HEAD`. Say so once if the primary checkout is dirty.
6. **Blocked** (`status: blocked`). Interactive: report the blocker and ask for another slug or to resume the existing worktree. Non-interactive: emit the handoff envelope with the blocker in `BLOCKERS:` and stop. Do not fall back to writing in the primary checkout without the user's explicit OK.
