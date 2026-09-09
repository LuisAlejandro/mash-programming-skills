# Learnings Researcher — prompt asset

Fallback for `rosey-learnings-researcher` when the named agent is not installed. Seed a generic subagent with this prompt plus the planning context summary. Read-only.

## Task

Search this repository's institutional memory for anything that should shape the plan described in the supplied planning context summary.

Look in:

1. **`rosey/solutions/`** — past fixes and how-tos. The highest-value hits are ones that solved a problem adjacent to this work, or that record a approach already tried and rejected.
2. **`rosey/insights/`** — durable repo lessons: architecture rules, workflow gotchas, "do not do this" entries.
3. **Prior plans** in `rosey/plans/` whose scope overlaps this work — particularly their Key Technical Decisions and any `Deferred to Follow-Up Work` items that this plan may now be picking up.

## What to return

For each hit: what it says, where it lives, and **why it bears on this plan**. A learning that does not change a decision, a boundary, or a risk is not worth reporting — the planner will not use it, and it dilutes the ones that matter.

Return nothing rather than padding when the search is genuinely empty; say the directories were searched and no relevant entry was found. That is a useful answer.

Do not restate the planning context back to the caller, and do not narrate the search.
