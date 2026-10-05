# Phase 4: Handoff

Loaded when Phase 3 has written every area document.

## 4.1 Present the area list

Show the epic's shape as a table, so the user can see the seams and the ordering before the run starts.

```text
Epic framed: <epic name> — <N> work areas.

| Area | Goal | Depends on | Document |
|---|---|---|---|
| user-panel-contract | Define the user record shape and its API schema | — | .mash/brainstorms/user-panel-contract-requirements.md |
| user-panel-crud-api | Read, create, update, and delete user records over the existing REST API | user-panel-contract | .mash/brainstorms/user-panel-crud-api-requirements.md |
| user-panel-list-view | Browse, search, and page through users | user-panel-contract | .mash/brainstorms/user-panel-list-view-requirements.md |
| user-panel-edit-view | Create and edit a single user record | user-panel-contract | .mash/brainstorms/user-panel-edit-view-requirements.md |
```

Use absolute paths for the document references in chat output — relative paths are not auto-linked as clickable in most terminals. Keep the repo-relative form inside the documents themselves.

State the expected shape in one line: how many areas can start immediately, and which wait on a dependency.

## 4.2 Hand off to `mash-epic-decompose`

Load the `mash-epic-decompose` skill in the current session, passing the area list: each area's id, goal, declared dependencies, and document path.

Do not print a closing summary first — the handoff continues the run.

**What decompose owns from here.** Say this plainly when handing off, so the boundary is visible:

- **File footprints** — which files each area is likely to touch. This phase produced product seams, not file lists.
- **Disjointness validation and collision resolution** — whether those footprints actually separate, and what to do when they do not. Merging areas onto one track or promoting a shared surface to a contract task is scheduling work and belongs to decompose.
- **The run inputs and the run itself** — decompose emits `run-inputs.json` and invokes `mash-parallel`.

The handoff is one-way. Framing does not wait for decompose's answer and the run does not return here.

## 4.3 Non-interactive mode

Skip the menu. Emit a compact envelope so an automated caller can consume the result without parsing prose:

```text
MASH_EPIC_FRAME_HANDOFF
AREAS: <comma-separated area ids, in dependency order>
DOCS: <comma-separated repo-relative document paths, same order>
DEPS: <area-id>:<dep-id>[,<dep-id>]; ... (omit areas with no dependencies)
BLOCKERS: <none, or what needs human judgment>
END_MASH_EPIC_FRAME_HANDOFF
```

Never halt silently. When the scope floor stopped the run, or an area could not be written safely, emit the envelope with the reason in `BLOCKERS:` and empty `AREAS:` — an opaque halt is indistinguishable from a hang to an automated caller.
