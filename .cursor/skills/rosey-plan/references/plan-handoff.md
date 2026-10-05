# Plan Handoff

This file contains post-plan-writing instructions: the ponytail sanity-check, post-generation options, optional document review, and issue creation. Load it after the plan file has been written and the confidence check (5.3.1-5.3.7) is complete.

## 5.3.8 Ponytail Sanity-Check

Before final checks, run a lightweight over-engineering pass on the plan's Implementation Units. This is the write-time gate: catch speculative abstractions, unneeded dependencies, and over-scoped units *before* `rosey-work` commits to them, when they are cheapest to cut.

For each Implementation Unit, ask the ponytail ladder:

1. Does this unit need to exist at all? (YAGNI — is it speculative scope?)
2. Does it reuse what already exists in the codebase, or does it plan a new abstraction/helper?
3. Does it reach for the standard library or a native platform feature before a new dependency?
4. Is the unit the minimum that works, or does it carry dead flexibility / config nobody sets / a layer with one caller?

Flag only concrete cuts with a one-line replacement, e.g.:

- `U3: yagni — "configurable retry policy" with no consumer. Hardcode the retry count until a second caller exists.`
- `U5: stdlib — hand-rolled date parsing. Use the stdlib datetime/dateutil already in the tree.`
- `U2: shrink — unit spans 3 files for one behavior. Collapse to one file.`

Do **not** flag: correctness, security, performance, or domain complexity the requirements genuinely require. Do not flag a unit's single smoke test / `assert` self-check — that is the ponytail minimum, not bloat.

**Routing:** Apply `safe_auto`-style cuts (drop a speculative unit, inline a one-caller abstraction) directly to the plan. Surface anything that changes scope or needs a user decision in a concise line above the post-generation menu. If nothing to cut, note `Ponytail: lean — no cuts.` and move on.

**Non-interactive mode:** Apply safe ponytail cuts without waiting. Scope-changing cuts go to blockers/open questions rather than waiting for a user decision.

## 5.3.9 Final Checks and Cleanup

Before proceeding to post-generation options:
- Confirm the plan is stronger in specific ways, not merely longer
- Confirm the planning boundary is intact
- Confirm origin decisions were preserved

If artifact-backed mode was used:
- Clean up the temporary scratch directory after the plan is safely updated
- If cleanup is not practical on the current platform, note where the artifacts were left

Write the markdown plan directly per `references/markdown-rendering.md`.

After all mutations in this run have settled (initial write, deepening synthesis, and safe ponytail cuts), the artifact at its path reflects the final state.

## 5.4 Post-Generation Options

**Non-interactive mode:** If `mode:non-interactive` is active, skip the interactive menu below and return control to the caller immediately. The plan file has been written and checked, but document review has not run; the caller may invoke `rosey-doc-review` separately when review is desired.

**Path format:** Use absolute paths for chat-output file references — relative paths are not auto-linked as clickable in most terminals.

**Question:** "Plan ready at `<absolute path to plan>`. What would you like to do next?"

**Options:**
1. **Start `rosey-work`** (recommended) - Begin implementing this plan in the current session
2. **Agent review of plan with `rosey-doc-review`** - Dispatch reviewer agents to check coherence, feasibility, scope, and role-specific risks; auto-apply safe fixes; route remaining findings interactively. Always shown.
3. **Create Issue** - Create a tracked GitHub issue from this plan
4. **Done for now** - Pause; the plan file is saved and can be resumed later

**Menu rendering:** Use the platform's blocking question tool (see Interaction Method in SKILL.md). When the blocking tool is unavailable or errors, fall back to numbered-list-in-chat rendering. Never silently skip the question.

Based on selection (the bare per-option routing is also stated inline in the SKILL.md so it cannot be missed when this reference is not loaded; the elaborate sub-flows below are the reason this reference still exists):
- **Start `rosey-work`** -> Invoke the `rosey-work` skill via the harness's skill-invocation primitive, passing the plan path as the skill argument. Match by capability — whatever loads and runs a named skill in the current tool list. Do not merely tell the user to invoke `rosey-work` themselves; fire the invocation now so the plan executes in this session.
- **Agent review of plan with `rosey-doc-review`** -> Invoke `rosey-doc-review` on the plan path without `mode:headless`. When it returns "Review complete", return to this menu and re-render all four options; the plan may have changed. If residual P0/P1 findings remain unaddressed, add a one-line nudge beside the menu and refer to this option by label, not number.
- **Create Issue** -> Follow the Issue Creation section below
- **Done for now** -> Display a brief confirmation that the plan file is saved and end the turn. Do not start follow-up work without an explicit further user prompt.
- **Free-form review requests** (e.g., the user types "review", "walk through", or "deep review" instead of picking a numbered option) -> route as if they had picked `Agent review of plan with rosey-doc-review`. Do not loop back to the menu without invoking the review.
- **Other free-form input** -> Accept revisions to the plan and loop back to options.

## Issue Creation

GitHub is the only tracker this skill writes to. When the user selects "Create Issue":

1. Create the issue with the GitHub CLI:

   ```bash
   gh issue create --title "<type>: <title>" --body-file <plan_path>
   ```

2. If `gh` is not installed or not authenticated, surface a clear error (e.g., "`gh` CLI not found — install it, run `gh auth login`, or create the issue manually") and return to the options. Do not substitute another tracker's CLI.

After issue creation:
- Display the issue URL
- Ask whether to proceed to `rosey-work` using the platform's blocking question tool
