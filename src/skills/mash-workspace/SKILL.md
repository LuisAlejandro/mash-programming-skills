---
name: mash-workspace
description: Shared coordination contract for running Mash Programming Skills workflows concurrently in one repository — run identity, workspace and resource leases, and fail-fast contention. Read this before any skill mutates a checkout, publishes an artifact, or uses a shared runtime resource.
---

# Mash Programming Skills Workspace

Single source of truth for **who owns what** while several workflows run at once in one repository. Read this skill whenever another skill references a run id, a workspace lease, a resource claim, or a contention blocker.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## What this guarantees, and what it does not

**Guarantee (for participants).** Every workflow that routes its mutations through this contract gets: a unique run identity, exclusive ownership of the workspace it writes, exclusive claims on shared runtime resources, and a loud blocker instead of silent sharing when something is already held.

**Participation requirement.** The guarantee holds only between participants. This is a cooperative contract enforced by one helper, not by the operating system or the harness.

**Explicit non-guarantees:**

- A writer outside the corpus — a human editor, an unrelated script, another agent framework — is **not** covered. Protecting against those is the user's responsibility.
- No multi-machine or network-filesystem coordination. Leases assume one local filesystem with reliable exclusive file creation, and liveness is only verifiable on the host that holds the lease.
- No semantic conflict resolution. Two workflows with contradictory goals can still produce a merge conflict or need a human decision; this contract makes that loud and safe, not automatic.

## When a skill must use this

| Situation | Required |
|---|---|
| About to edit files in a checkout or worktree | Register a run, hold a `workspace` lease on that root |
| About to publish or move a branch | Hold a `baseref` lease for the publication window |
| About to use a port, container project, database, browser profile, or run a release | Hold the matching resource claim |
| Finishing, or stopping on a blocker | `run end` — releases every lease this run owns, and nothing else |

A read-only workflow does not need a lease, but it must report the revision it analyzed, because the tree can move underneath it.

## Helper

`scripts/workspace.py` is stdlib-only, runs under a plain `python3`, and prints JSON. Resolve its absolute path once from this skill's directory; relative skill paths do not survive an arbitrary working directory.

`--repo` accepts any directory inside the target repository and may appear before or after the subcommand. State lives under the **primary** checkout's gitignored `.mash/`, so every linked worktree coordinates through the same root.

```bash
HELPER="<skills dir>/mash-workspace/scripts/workspace.py"
REPO="$(git rev-parse --show-toplevel)"

# Register, then claim what this run will write.
RUN=$(python3 "$HELPER" run start --workflow work --workspace "$REPO" --repo "$REPO" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
python3 "$HELPER" lease acquire --run "$RUN" --kind workspace --key "$REPO" --repo "$REPO"

# ... do the work, refreshing liveness on long runs ...
python3 "$HELPER" run heartbeat --run "$RUN" --repo "$REPO"

# Always release, including on a blocker.
python3 "$HELPER" run end --run "$RUN" --repo "$REPO"
```

Lease kinds: `workspace`, `baseref`, `port`, `compose`, `db`, `browser`, `release`.

## Reading the result

Exit `0` means success. Exit `2` is a refusal or contention and always carries a payload:

```json
{
  "status": "blocked",
  "kind": "workspace",
  "key": "/path/to/checkout",
  "blocker": "workspace:/path/to/checkout is held by run 20261103-150000-9f2a: owner pid 4412 is still alive",
  "holder": { "run_id": "...", "pid": 4412, "host": "...", "agent": "pi", "age_seconds": 12.4 },
  "recovery": ["wait for the holder to finish and retry", "use a different workspace or resource", "..."]
}
```

**Contention fails fast.** Do not wait silently, do not retry in a loop, and do not proceed without the lease. Report the holder and the recovery options: in interactive mode as a blocker the user can act on, in non-interactive mode through the skill's handoff envelope `BLOCKERS:` field.

`run end` is required on every exit path, including a blocked one — otherwise the run's other leases stay held until the stale window expires.

## Liveness and reclaim

A lease is reclaimed only when **all** of these hold: it was taken on this host, its owner process is gone, and its heartbeat has been silent past the stale window (default 300s). A live owner is never displaced, and a lease written by another host is never reclaimed, because liveness cannot be verified there.

Long-running work should call `run heartbeat` periodically so a slow run is never mistaken for a dead one.

## Rules

- Never delete, unlock, or overwrite a lease you do not own. Release refuses when the run id does not match.
- Never reuse another run's workspace because the name matches. Identity is the run, not the slug.
- Register before mutating, not after.
- Treat an unregistered workspace from an older session as unowned: adopt it explicitly rather than assuming it is free.
- Do not store secrets in run records; they are plain JSON under `.mash/`.
