# Phase 3: Capture the Requirements

Write or update a requirements document only when the conversation produced durable decisions worth preserving — see `references/brainstorm-sections.md` "Decide whether a doc is warranted at all" for the criteria and the bug-fix stress test. Skip document creation when the user only needs brief alignment and the decisions can flow downstream (rosey-plan, commit message, `rosey/solutions/`) without a brainstorm artifact in the middle.

In non-interactive mode a document is always written. A caller that cannot see chat has no other way to receive the result, so the skip rule above is interactive-only; if a concrete document cannot be written safely, stop with a blocker instead of returning prose.

When a doc is warranted, compose it using:

- `references/brainstorm-sections.md` — section contract (outcomes, hard floor, include-when-material catalog, agency rules, ID conventions).
- `references/markdown-rendering.md` — how to present the sections in markdown.

**Write tight.** A section being material is not license to pad it. Lead with the decision or outcome, one idea per sentence, a requirement is intent plus at most one qualifier, defer forks to Outstanding Questions rather than specifying both arms, and resolve superseded text in place rather than stacking strata.

Write to `rosey/brainstorms/YYYY-MM-DD-<topic>-requirements.md`. Confirm with the absolute path so the reference is clickable.
