# Handoff

This content is loaded when Phase 4 begins, after the requirements document is written. Every software run has a document by this point.

---

#### 4.1 Present Next-Step Options

If `INTERACTION_MODE=non-interactive`, skip this menu. Emit the envelope with **repo-relative** paths (empty `REQUIREMENTS PATH` when blocked). Do not use absolute paths here.

```text
MASH_BRAINSTORM_HANDOFF
REQUIREMENTS PATH: <repo-relative, empty when blocked>
DOSSIER PATH: <repo-relative or none>
BLOCKERS: <none | one-line>
ASSUMPTIONS: <none | one-line>
END_MASH_BRAINSTORM_HANDOFF
```

The Phase 4 menu has at most four options. Use the Interaction Method contract in `references/interaction-rules.md`. Never silently skip the question.

If `Resolve Before Planning` contains any items:
- Ask the blocking questions now, one at a time, by default
- If the user explicitly wants to proceed anyway, first convert each remaining item into an explicit decision, assumption, or `Deferred to Planning` question
- If the user chooses to pause instead, present the handoff as paused or blocked rather than complete
- Do not offer the `Plan implementation` option while `Resolve Before Planning` remains non-empty

In both preambles below, the "Pick a number or describe what you want." hint applies only in numbered-list fallback. When using the blocking tool, omit that line and pass the remaining stem as the question.

**Path format:** Use absolute paths for **interactive chat** file references — relative paths are not auto-linked as clickable in most terminals. The non-interactive envelope uses repo-relative paths only.

**Preamble when no blocking questions remain:**

```
Brainstorm complete.

Requirements doc: <absolute path to requirements doc>

What would you like to do next? (Pick a number or describe what you want.)
```

**Preamble when blocking questions remain and user wants to pause:**

```
Brainstorm paused. Planning is blocked until the remaining questions are resolved.

Requirements doc: <absolute path to requirements doc>

What would you like to do next? (Pick a number or describe what you want.)
```

Present only the options that apply. Renumber so visible options stay contiguous starting at 1.

1. **Plan implementation with `mash-plan` (Recommended)** - Move to `mash-plan` for structured implementation planning. Shown only when `Resolve Before Planning` is empty.
2. **Agent review of requirements doc with `mash-doc-review`** - Dispatch reviewer agents to check the doc for coherence, feasibility, scope, and other persona-specific issues; auto-apply safe fixes; route remaining findings interactively. Always shown.
3. **More clarifying questions to sharpen the scope** - Keep refining scope, edge cases, constraints, and preferences through further dialogue. Always shown.
4. **Done for now** - Pause; the requirements doc written this run is saved and can be resumed later. Always shown.

**There is no direct-to-work route.** The pipeline is `mash-brainstorm` → `mash-plan` → `mash-work`, and planning is not skippable: `mash-work` executes a plan, so work that entered a brainstorm leaves it through `mash-plan`. Work narrow enough to implement without a plan does not belong in this skill at all — see the scope floor in `SKILL.md`.

**Post-review nudge (subsequent rounds only):** If the user has already run `mash-doc-review` this session and residual P0/P1 findings remain unaddressed, add a one-line prose nudge adjacent to the menu (e.g., "Document review flagged 2 P1 findings you may want to address — pick \"Agent review of requirements doc\" to run another pass."). Reference the option by label, not number: the menu renumbers when `Resolve Before Planning` hides `Plan implementation`, so a hardcoded option number can point users at the wrong action. Do not add a separate menu option; reuse the existing agent-review option.

#### 4.2 Handle the Selected Option

Selections may be the literal option label (when the user types the label or a close paraphrase) or the option number. Match numbers against the currently-rendered (post-trim) list. Free-form input that doesn't match an option or describe an alternative action should be treated as clarification — ask a follow-up rather than guessing.

**If user selects "Plan implementation with `mash-plan` (Recommended)":**

Immediately load the `mash-plan` skill in the current session. Pass the requirements document path — `mash-plan` requires it as origin and stops without one. When the Phase 1.1 grounding scout produced a dossier and the file still exists, also pass its path — prefer repo-relative; `mash-plan` resolves it from the worktree root. Do not print the closing summary first.

**If user selects "Agent review of requirements doc with `mash-doc-review`":**

Load the `mash-doc-review` skill, passing the requirements document path as the argument. When mash-doc-review returns "Review complete", return to the Phase 4 options and re-render the menu (the doc may have changed, so re-evaluate `Resolve Before Planning` and residual findings). If residual P0/P1 findings remain unaddressed, include the post-review nudge above the menu. Do not show the closing summary yet.

**If user selects "More clarifying questions to sharpen the scope":** Return to Phase 1.3 (Collaborative Dialogue) and continue asking the user clarifying questions one at a time to further refine scope, edge cases, constraints, and preferences. Continue until the user is satisfied, then return to Phase 4. Do not show the closing summary yet.

**If user selects "Done for now":** Display the closing summary (see 4.3) and end the turn.

#### 4.3 Closing Summary

Use the closing summary only when this run of the workflow is ending or handing off, not when returning to the Phase 4 options.

In both templates below, substitute `<absolute path to requirements doc>` with the actual `.md` file path written this run.

When complete and ready for planning, display:

```text
Brainstorm complete!

Requirements doc: <absolute path to requirements doc>

Key decisions:
- [Decision 1]
- [Decision 2]

Recommended next step: `mash-plan`
```

If the user pauses with `Resolve Before Planning` still populated, display:

```text
Brainstorm paused.

Requirements doc: <absolute path to requirements doc>

Planning is blocked by:
- [Blocking question 1]
- [Blocking question 2]

Resume with `mash-brainstorm` when ready to resolve these before planning.
```
