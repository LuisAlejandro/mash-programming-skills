---
name: write-technical-article
description: >-
  Writes a Cosmic-ready technical article for luisalejandro.org from source code
  in the current workspace (how-it-works, how-we-solved-it, tutorials with code,
  commands, diagrams, and tables). Runs gist-working-example first so readers can
  clone a public gist; the article quotes those files. Saves to frontdesk
  scripts/luisalejandro.org/output and asks before publishing via make blog-post
  / blog-publish. Use when the user asks to write a technical blog post from code,
  a luisalejandro.org article, or to explain a codebase as a published tutorial.
---

# Write Technical Article

Personal skill. Invoke by name (`/write-technical-article` or @ this skill). Writes the Cosmic output file **directly** — do **not** run `make blog-generator` or the Gemini Engineer pipeline.

Always read [format.md](format.md) before drafting. Read [examples.md](examples.md) if voice or structure is uncertain.

After reading the source code and **before** drafting, read and execute `~/.cursor/skills/gist-working-example/SKILL.md` to completion. Do not write the Cosmic markdown until a handoff block with a non-empty `GIST_URL` exists. If the user declines the gist, stop — do not write the article.

## Paths

```bash
FRONTDESK_ROOT="${FRONTDESK_ROOT:-/Volumes/Documents/Software/frontdesk}"
OUTPUT_DIR="$FRONTDESK_ROOT/scripts/luisalejandro.org/output"
IMAGES_DIR="$OUTPUT_DIR/images"
```

Confirm `$OUTPUT_DIR` exists. If the default root is missing, stop and ask. Do not invent another blog repo.

Source code lives in the **current workspace**. The article always lands in `$OUTPUT_DIR`, even when cwd is another project.

## Workflow

Copy and track:

```
- [ ] 1. Resolve FRONTDESK_ROOT
- [ ] 2. Read named source code
- [ ] 3. Run gist-working-example (stop if no GIST_URL)
- [ ] 4. Read format.md
- [ ] 5. Draft + hero + write output file (quote gist files only)
- [ ] 6. Ask to publish (stop until the user answers)
- [ ] 7. If yes: scoped blog-post, then scoped blog-publish
```

### 1. Topic and sources

Collect from the user: what to explain, which files/paths, any angle (how-to, postmortem, architecture). If they attached a file, that is the primary source.

Read that code in the current workspace. Follow imports only as far as needed. **Do not invent APIs, flags, or behavior.** If the code is unclear, ask; do not guess.

Strip secrets: no tokens, passwords, `.env` values, Cosmic keys, or private URLs.

### 2. Working gist (required)

Read `~/.cursor/skills/gist-working-example/SKILL.md` (absolute path; any workspace) and follow it now. Pass the same topic and source paths.

Wait for the handoff block (`GIST_URL`, `GIST_ID`, `CLONE`, `FILES`). Empty `GIST_URL` or a declined gist: **stop**. Do not draft.

This gate is separate from Cosmic publish. Creating the gist does not publish the blog post.

### 3. Draft the article

Language: Venezuelan Spanish (`tú`) unless the user explicitly asks for English. Keep English technical terms (`commit`, `hook`, `pipeline`).

Structure (see format.md): no H1 in the body; intro (2–4 sentences) → numbered `### 1. …` sections → exact GitHub footer.

Link `GIST_URL` in the intro or `### 1.`. Put the handoff `CLONE` command in a `bash` fence (must match `CLONE` exactly). Every **runnable** code fence must be a verbatim excerpt of a named gist file (or a contiguous excerpt of that file). Clone/run commands in the article must match the gist `README.md` except the clone URL, which comes from `CLONE`.

`❌ Incorrecto` pitfalls may be original. Pseudocode is allowed. Do not invent a second copy of the working example.

Tables only when comparing options. For architecture/flow diagrams, generate images (below) — mermaid is not the published diagram unless the user asks for mermaid in the source file as an extra.

### 4. Hero (required) and optional diagrams

Cosmic expects a hero. Use the GenerateImage tool, then copy the file into `$IMAGES_DIR` (create the dir if needed):

```bash
cp "<generated-file>" "$IMAGES_DIR/<kebab-name>.jpg"
```

Frontmatter: `hero: images/<kebab-name>.jpg`

Inline diagrams: 0–2 extra images. In the **body**, use markdown so `blog-post` can upload them:

```markdown
![short alt describing the diagram](images/<kebab-name>.jpg)
```

Do not write Cosmic `<span class="figure">` HTML in a new file. That form appears only after upload. Do not leave mermaid as the only diagram.

### 5. Write the output file

Filename: `YY-MM-DD-<slug>-generated.md` (local date, two-digit year). Slug from the title using the rules in format.md.

If that path already exists, do not overwrite — ask, or suffix `-2` before `-generated`.

Write YAML frontmatter + body in one file. `post_id: null`, `published: false`.

### 6. Publish gate (hard)

After the file is on disk, show the user: absolute path, title, slug, teaser. Then **ask** whether to publish to luisalejandro.org.

- **No / not yet:** stop. Leave the file. Do not run Make. Do not commit.
- **Yes:** run both scoped commands below, in order. Report stdout/stderr.
- Never auto-publish. Never commit unless the user asks in a later turn.

### 7. Scoped Make only

Run from any cwd via `-C`. `blog-post` already depends on `stat` (starts the app container).

```bash
make -C "$FRONTDESK_ROOT" blog-post output="<basename>.md"
make -C "$FRONTDESK_ROOT" blog-publish slug="<slug>"
```

`<basename>.md` is the file name only (e.g. `26-08-15-mi-tema-generated.md`). `<slug>` is the frontmatter `slug`.

**Forbidden:**

- `make blog-post` or `make blog-publish` without `output=` / `slug=` (processes **every** unpublished file / **every** Cosmic draft)
- Host `npx tsx scripts/luisalejandro.org/...` — if Make/Docker/Cosmic fails, stop and report the error
- `make blog-generator`

## Categories

Reuse an existing Cosmic name. Prefer: `Desarrollo de Software`, `DevOps`, `Inteligencia Artificial y Tecnología`. Do not invent near-duplicates (`Desarrollo de Software e IA`, `LLMOps y …`) unless the user names one.

## Additional resources

- [format.md](format.md) — frontmatter, voice, body, footer, gist citation
- [examples.md](examples.md) — IMAP-style excerpt, gist citation, image syntax, anti-example
- `~/.cursor/skills/gist-working-example/SKILL.md` — public gist before draft
