# Diff Scope Rules (live-home)

These rules apply to every reviewer. The home is dirty by default. Review only this session's files.

## Scope Discovery

1. **User or handoff scope.** `FILES_CHANGED`, `BASE:`, `FILES:`, or `DIFF:` from the orchestrator — use that list exactly.
2. **Session tracked changes.** `git diff HEAD -- <session files>`.
3. **Session untracked.** Untracked paths in `FILES_CHANGED` are in scope. Other untracked files in the home are out of scope — do not ask anyone to `git add` them.

Do not expand scope to "all unpushed commits vs origin/master" unless the user passed `base:` or asked to review those commits. Mixed historical WIP on master is expected.

## Finding Classification Tiers

Same primary / secondary / pre-existing split as the product skill, but "pre-existing" also includes dirty files this session did not touch. Do not file findings against unrelated in-progress work.
