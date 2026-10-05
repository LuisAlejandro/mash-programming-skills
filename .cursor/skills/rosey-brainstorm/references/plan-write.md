# Phase 3: Capture the Requirements

Write or update a requirements document on every **software** run. The document is the pipeline's contract with `rosey-plan`, which requires it as origin, and in non-interactive mode it is the only channel back to a caller that cannot see chat. If a concrete document cannot be written safely, stop with a blocker instead of returning prose. Non-software runs write a file only when the user saves or chooses Create a plan.

Compose it using:

- `references/brainstorm-sections.md` — section contract (outcomes, hard floor, include-when-material catalog, agency rules, ID conventions).
- `references/markdown-rendering.md` — how to present the sections in markdown.

**Write tight.** A section being material is not license to pad it. Lead with the decision or outcome, one idea per sentence, a requirement is intent plus at most one qualifier, defer forks to Outstanding Questions rather than specifying both arms, and resolve superseded text in place rather than stacking strata.

Write to `rosey/brainstorms/YYYY-MM-DD-<topic>-requirements.md`. Confirm with the absolute path so the reference is clickable.
