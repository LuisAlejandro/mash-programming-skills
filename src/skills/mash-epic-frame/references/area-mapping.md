# Phase 2: Draw the Areas

Phase 0 established that there is more than one outcome and produced a candidate list. Phase 1 grounded each one. This phase settles the final seams, names them, and declares their dependencies.

## Slice on product seams

A seam is where **user value** separates, not where code separates. Four seams recur:

**Shared surface vs. its consumers.** When several outcomes need the same types, schema, or interface, that surface is its own area and the others depend on it. This is the most valuable seam to find: it is what lets the consumers run in parallel afterward, and `mash-epic-decompose` promotes it to a contract task.

**Producer vs. consumer.** A backend capability and the interface that uses it are usually two areas — each has its own acceptance boundary, and the interface can be verified against a stubbed or already-shipped producer. Split them when the backend work is substantial enough to stand alone; keep them together when the "backend" is one endpoint that exists only to serve one view.

**View vs. view.** Separate screens or flows are separate areas when each delivers value on its own. A list and a detail editor are two areas. A form and its own validation are one.

**Existing extension vs. new construction.** Extending something established and building something new have different risk and different acceptance shapes, even inside one nominal feature.

### What is not a seam

- **Coverage.** Several providers, devices, or data sources behind one path is one area with several requirements.
- **Layers within one outcome.** A component, its styles, and its tests are one area.
- **Sequence.** "First X, then Y" is a dependency, not necessarily two areas — if Y cannot be verified without X being finished, they are one area.
- **Effort.** A large area is still one area. Split on value boundaries, never on size.

## Merge or split

| Signal | Action |
|---|---|
| An area cannot be verified without another finishing first | Merge them |
| An area's requirements keep referencing another area's behavior | Merge, or extract the shared part as its own area |
| Two areas would both define the same type or schema | Extract that surface as its own area; both depend on it |
| One area serves two unrelated actors with separate acceptance | Split |
| An area exists only to hold "the rest" | Dissolve it into the areas it actually belongs to |

## Granularity

**Two to five areas is the common shape.** Beyond that, check the seams: many small areas usually means slicing on layers or coverage rather than value.

- **One area** — not an epic. Phase 0's scope floor should have caught this; if the dialogue collapsed the areas, stop and say so.
- **Twenty or more** — the seams are too fine. Group them into the value boundaries a user would recognize.

## Area ids

Each area gets a **lowercase-hyphen slug**. The id is load-bearing: it becomes the task id downstream and it determines the requirements-document filename.

Rules:

- Lowercase letters, digits, and hyphens only. No underscores, spaces, or capitals — anything else is rewritten downstream and the id stops round-tripping.
- **Name the epic in the id.** Requirements documents live in one flat directory shared with every other epic. `api` and `frontend` will collide; `user-panel-api` and `user-panel-list-view` will not. A collision silently binds one epic's area to another epic's document.
- Say what the area delivers, not what layer it lives in.

Good: `user-panel-contract`, `user-panel-crud-api`, `user-panel-list-view`, `user-panel-edit-view`.
Bad: `api`, `frontend`, `part-2`, `user_panel_API`.

## Declare dependencies

A dependency means **area B consumes something area A defines** — a type, a schema, an endpoint contract, a component interface. Declare those.

**Do not declare file overlap.** Two areas touching the same file is a scheduling fact, and `mash-epic-decompose` derives it from footprints. Declaring it here serializes work that could have run in parallel.

**Do not over-declare.** Every dependency edge removes parallelism. If area B could start against a stub or an agreed shape, it does not depend on area A finishing.

Express dependencies as area ids, and keep them acyclic — a cycle means the seam is wrong, not that the ordering is complex.

## Where framing stops

Areas are drawn on product seams. `mash-epic-decompose` then derives file footprints and checks whether those seams are also file-disjoint. They usually are; sometimes they are not.

**A file-level collision is decompose's to resolve, not framing's.** Merging two areas onto one track, or promoting a shared surface to a contract task, is scheduling work — it belongs to the skill that owns footprints and sequencing. This phase does not wait for that answer and the run does not come back here.

The consequence is worth knowing: when decompose merges two areas onto one track, both of their requirements documents stay valid and the merged task carries both. That is correct — the documents describe product scope, and product scope did not change because two areas share a file.

Footprints, disjointness validation, collision resolution, and the run inputs all stay with `mash-epic-decompose`. This phase supplies the product seams and the declared dependencies, and hands off.
