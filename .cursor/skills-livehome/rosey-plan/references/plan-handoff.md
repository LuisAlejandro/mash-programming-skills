# Plan Handoff (live-home)

This file contains post-plan-writing instructions: document review and post-generation options. Load it after the plan file has been written and the confidence check (5.3.1-5.3.7) is complete.

Do not offer Create Issue or Create PR. Git is backup/sync, not a collaboration surface.

## 5.3.8 Document Review

Run the `rosey-doc-review` skill with `mode:headless` on the plan file. Pass `mode:headless <plan-path>` as the skill arguments. When this step is reached, it is mandatory — do not skip it because the confidence check already ran. The two tools catch different classes of issues.

Headless is the default at this phase because most users want to start work after planning, not adjudicate every reviewer concern up front. Headless applies `safe_auto` fixes silently and returns structured findings text — no walkthrough, no per-finding routing, no blocking prompts. The post-generation menu (see 5.4) offers `Run deeper doc review` as a first-class option so users can opt into the full interactive walkthrough when they want it.

The confidence check and rosey-doc-review are complementary:
- The confidence check strengthens rationale, sequencing, risk treatment, and grounding
- Document-review checks coherence, feasibility, scope alignment, and surfaces role-specific issues

Capture the headless envelope so it can drive the contextual summary above the post-generation menu:
- The number of fixes auto-applied
- The count of remaining findings, broken out by user-facing bucket (proposed fixes, decisions, FYI observations)
- The severity breakdown of decisions and proposed fixes (specifically the P0/P1 count, since those benefit from explicit user attention)

When rosey-doc-review returns "Review complete", proceed to Final Checks.

**Non-interactive mode:** Non-interactive planning always invokes `rosey-doc-review` with `mode:headless` and the plan path — the headless mode is identical to the interactive default at this phase. No further routing is offered in non-interactive mode; the caller decides what to do with the returned findings. Address any P0/P1 findings before returning control to the caller.

## 5.3.9 Final Checks and Cleanup

Before proceeding to post-generation options:
- Confirm the plan is stronger in specific ways, not merely longer
- Confirm the planning boundary is intact
- Confirm origin decisions were preserved when an origin document exists
- Confirm the plan does not invent feature branches, worktrees, or PRs. Implementation lands on `master`/`main`.

If artifact-backed mode was used:
- Clean up the temporary scratch directory after the plan is safely updated
- If cleanup is not practical on the current platform, note where the artifacts were left

Write the markdown plan directly per `references/markdown-rendering.md`.

After all mutations in this run have settled (initial write, deepening synthesis, rosey-doc-review `safe_auto` fixes), the artifact at its path reflects the final state.

## 5.4 Post-Generation Options

**Non-interactive mode:** If `mode:non-interactive` is active, skip the interactive menu below and return control to the caller immediately. The plan file has already been written, the confidence check has already run, and rosey-doc-review has already run — the caller determines the next step.

**Path format:** Use absolute paths for chat-output file references — relative paths are not auto-linked as clickable in most terminals.

**Summary line above the menu (always):** Print a single concise line summarizing the headless review state — e.g., `Doc review applied 3 fixes. 2 decisions, 1 proposed fix, 4 FYI observations remain (1 at P1).` When no fixes were applied and no findings remain, print `Doc review clean — no fixes needed.` This line establishes what the autofix pass did so the user has the context to choose between the menu options below.

**Question:** "Plan ready at `<absolute path to plan>`. What would you like to do next?"

**Options:**

1. **Start `/rosey-work`** (recommended) — implement on `master`/`main` in this session
2. **Run deeper doc review** — Walk through the remaining findings interactively (full rosey-doc-review walkthrough)
3. **Done for now** — pause; the plan file is saved

Do not offer Create Issue or Create PR.

**Menu rendering:** Count visible options after applying the hide rules below. When **4 or fewer** options remain, use the platform's blocking question tool (`AskUserQuestion` in Claude Code — call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded; `request_user_input` in Codex; `ask_user` in Gemini/Pi). When the blocking tool is unavailable or errors, fall back to numbered-list-in-chat rendering. Never silently skip the question.

**Hide `Run deeper doc review` when no actionable findings remain.** Show option 2 only when the headless envelope reports `proposed_fixes_count + decisions_count > 0` — i.e., at least one `gated_auto` or `manual` finding at confidence anchor `75` or `100`. Drop the option in any other case, including FYI-only state. After trimming, renumber visible options contiguously starting at 1.

Based on selection:
- **Start `/rosey-work`** -> Invoke the `rosey-work` skill via the platform's skill-invocation primitive, passing the plan path as the skill argument. Do not merely tell the user to type `/rosey-work` — fire the invocation now so the plan executes in this session.
- **Run deeper doc review** -> Re-invoke the `rosey-doc-review` skill on the plan path **without** `mode:headless`. After it returns, re-render this menu with the refreshed counts so the user can pick what to do next.
- **Done for now** -> Display a brief confirmation that the plan file is saved and end the turn. Do not start follow-up work without an explicit further user prompt.
- **Free-form prompts that target the findings** (e.g., the user types "review", "walk through", "deep review" instead of picking a numbered option) -> route as if they had picked `Run deeper doc review`.
- **Other free-form input** -> Accept revisions to the plan and loop back to options.
