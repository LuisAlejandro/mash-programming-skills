# DOCS-LOOP LEDGER

> Single-repository iterative audit ledger. Updated once per pass by docs-loop-iteration.

## Run

- state format: 1
- scope: {{WORKSPACE_ROOT}}
- mode: APPLY
- state directory: {{STATE_DIR}}
- started: {{STARTED_AT}}
- passes: 0
- clean_passes: 0
- failures: 0
- result: IN-PROGRESS

## Pass log

- pass 0: outcome STARTED

## Stop states

- `SUCCESS`: `clean_passes` reached the clean-passes limit — docs fully updated and audited.
- `BUDGET`: `passes` reached max iterations.
- `ERROR`: unrecoverable failure or `failures` reached the failure limit.
- `BLOCKED`: genuine human-only decision or external dependency.

## Integration markers

- integration branch: (set by the pass once per segment)
- integration worktree: (set by the pass once per segment)
