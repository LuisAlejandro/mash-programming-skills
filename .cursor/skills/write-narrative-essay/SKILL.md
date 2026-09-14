---
name: write-narrative-essay
description: >-
  Configures a narrative essay for luisalejandro.org: short interview, one
  narrative YAML input, then frontdesk generate. Asks before Cosmic via scoped
  make blog-post / blog-publish. Use for literary, story, or essay posts — not
  tutorials. Do not use write-technical-article for essays; that skill drafts
  Cosmic markdown itself and is the wrong tool here. Frontdesk Writer writes
  the essay; this skill does not.
---

# Write Narrative Essay

Personal skill. Invoke by name (`/write-narrative-essay` or @ this skill).

Frontdesk **writes** the essay. This skill only interviews, writes one `narrative` input, runs scoped generate, and asks before Cosmic.

**Wrong tool:** `write-technical-article` (gist, hand-drafted Cosmic markdown, no `blog-generator`). Do not follow that skill’s draft rules. Do not require a gist.

Always read the flag block from `scripts/luisalejandro.org/input/25-11-26-imagenes-en-ia-nos-son-distinguibles.md` before writing YAML (copy those keys; do not copy `processed: true` or its `questions`).

## Paths

```bash
FRONTDESK_ROOT="${FRONTDESK_ROOT:-/Volumes/Documents/Software/frontdesk}"
INPUT_DIR="$FRONTDESK_ROOT/scripts/luisalejandro.org/input"
OUTPUT_DIR="$FRONTDESK_ROOT/scripts/luisalejandro.org/output"
```

Confirm `$INPUT_DIR` and `$OUTPUT_DIR` exist. If the default root is missing, **stop and ask**. Do not invent another blog repo.

The author may invoke this from any workspace. Input and generated files always land under `$FRONTDESK_ROOT`, never in cwd.

## Workflow

Copy and track:

```
- [ ] 1. Resolve FRONTDESK_ROOT (input + output dirs)
- [ ] 2. Named file or same-chat leftover? Resolve generated path (below)
- [ ] 3. If new post: interview, then write one narrative input
- [ ] 4. Scoped blog-generator for that file only
- [ ] 5. Publish gate: show path, title, slug, teaser, then ask
- [ ] 6. If yes: scoped blog-post, check post_id, then scoped blog-publish
- [ ] 7. Never git-commit unless the author asks in a later turn
```

### 1. Topic

Collect a one-line premise (or a topic with no YAML yet). If they already named an existing input or `*-generated.md` file, or this chat already generated, go to **§2**.

### 2. Named file or leftover

Resolve the generated path first:

- Author named `*-generated.md` → that file.
- Author named an input basename → `$OUTPUT_DIR/<stem>-generated.md`.
- Same chat after Cosmic no / not yet → the generated file from this chat.

Do **not** search the output folder by matching the premise. A new premise always takes interview → one new input → generate.

**Generated file exists (Cosmic-only re-entry):** do **not** interview, do **not** write a new input, do **not** run generate. Go to **Publish gate**.

**Generated file missing:**

- Input exists and `processed: false` (or generate never succeeded this chat): do **not** skip generate. Interview only if the YAML is missing. Then scoped `blog-generator input=<that file>`.
- `processed: true` and generated missing: **stop**. Do not run unscoped `blog-generator`.
- Same-chat publish: require a generated file from this chat, not merely that generate was attempted.

### 3. Interview (new posts only)

Ask **two or three** questions, then write the file. Do not dump YAML from the premise alone. Do not pause for YAML approval.

1. Angle or story shape?
2. Who is this for?
3. Anything that must appear?

Do **not** add questions for language, length, country, or essay flags. Change those YAML fields only when an answer **clearly names** a language or a word count. Otherwise keep the Nano Banana defaults.

### 4. Write one narrative input

Filename: `YY-MM-DD-<ascii-slug>.md` (local date, two-digit year). Slug: lowercase, hyphens, first ~7 words of the premise; strip characters outside `[a-z0-9-]`. If that path already exists for a **different** post, suffix `-2` / `-3` before `.md`. Never overwrite.

Generate-fail retry uses the **same** filename and the same `input=`. Re-entry does not write a file.

Write YAML from scratch. **Never** run `make blog-create-template`.

Omit `questions` and `voice_author`. Never omit `target_audience`: if the interview audience is blank, use `lectores de literatura reflexiva y crítica`.

Map:

| Interview | YAML |
| --- | --- |
| One-line topic | `premise` (keep this; do not replace it with the angle) |
| Angle + must-include | `context` (list of strings) |
| Audience | `target_audience` |

Writer only sees restatement of `premise`, `language`, `target_audience`, `word_count`, and `context`. Country and boolean flags are copied for YAML parity; they do not steer the narrative Writer. Hero still runs from generate. **Do not promise inline illustrations.**

```yaml
---
post_type: narrative
processed: false
premise: >-
  <one-line premise>
context:
  - <angle>
  - <must-include, if any>
language: español
country: latinoamerica
target_audience: <interview audience or lectores de literatura reflexiva y crítica>
word_count: 1500
suggest_images: true
suggest_code_examples: false
include_tables: false
include_lists: false
reference_author: false
spark_debate: true
---
```

### 5. Generate (this file only)

```bash
make -C "$FRONTDESK_ROOT" blog-generator input="<basename>.md"
```

`<basename>.md` is the input file name only (e.g. `26-08-15-mi-ensayo.md`).

Generate logs a checkmark, not title/slug/teaser. On success, go to **Publish gate**.

On Docker / Gemini / Make failure: report stderr. Do not run Cosmic. `processed` stays false. Retry only the same `input=`. Never retry without `input=`.

### 6. Publish gate (hard)

Read `$OUTPUT_DIR/<basename>-generated.md` (or the resolved generated path from §2). Before asking, show the author: **absolute path**, **title**, **slug**, **teaser** from that file’s frontmatter. If those four cannot be read, **stop**. Do not ask. Do not run Cosmic.

Ask whether to publish to luisalejandro.org.

- **No / not yet:** stop. Leave the files. Do not run Cosmic. Do not commit.
- **Yes:** run both scoped commands below, in order. Report stdout/stderr.
- Never auto-publish. Never commit unless the author asks in a later turn — including after a successful publish.

### 7. Scoped Make only

Run from any cwd via `-C`. These targets already depend on `stat` (starts the app container).

```bash
make -C "$FRONTDESK_ROOT" blog-post output="<basename>-generated.md"
```

Then re-read the generated file’s frontmatter. If `post_id` is null or missing, treat draft as failed: **stop**. Do not run `blog-publish`. Make exit 0 is not proof of a Cosmic insert.

```bash
make -C "$FRONTDESK_ROOT" blog-publish slug="<slug>"
```

`<slug>` is the frontmatter `slug`. If publish fails after a successful draft, retry **only** this `blog-publish slug=` line. Do not re-generate. Do not omit `slug=`.

`blog-publish slug=` still publishes all Cosmic **draft categories**. That is known Make behavior. Do not invent a new target or run unscoped publish to “fix” it.

**Forbidden:**

- `make blog-generator` / `blog-post` / `blog-publish` without `input=` / `output=` / `slug=` (processes **every** pending file / **every** Cosmic draft)
- Empty `input=` / `output=` / `slug=` (Make treats empty as unset)
- Host `npx tsx scripts/luisalejandro.org/...` — if Make/Docker/Cosmic fails, stop and report
- `make blog-create-template`
- `make blog-generator` from `write-technical-article` rules (that skill forbids generate; this one **requires** scoped generate)
- Drafting the essay body in this skill
- Gist gate
- Git commit unless the author asks later

## Failure table

| Case | Do |
| --- | --- |
| Missing `FRONTDESK_ROOT` / input / output dir | Stop and ask. Do not invent a repo. |
| Generate fail (Docker, `.env`, `GEMINI_API_KEY`) | Report stderr. No Cosmic. No commit. Retry same `input=`. |
| Named input, generated missing, `processed: false` | Interview only if YAML missing. Scoped generate that file. No Cosmic until after generate. |
| Generated file missing, `processed: true` | Stop. Do not process the folder. |
| Publish gate cannot read path/title/slug/teaser | Stop. Do not ask. Do not run Cosmic. |
| Cosmic draft fail (`post_id` still null) | Stop. Do not publish. Retry only scoped `blog-post output=`. |
| Cosmic publish fail after draft | Report. Retry only scoped `blog-publish slug=`. |
| Ambiguous Cosmic answer | Wait. Only a clear yes runs Make. |

## Categories

Reuse an existing Cosmic name when the generator’s metadata already set one. Do not invent near-duplicates. This skill does not pick categories by hand unless generate left them empty and the author names one.
