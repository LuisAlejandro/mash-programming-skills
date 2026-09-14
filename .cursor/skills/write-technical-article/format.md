# Article format (luisalejandro.org Cosmic output)

Match files in `$FRONTDESK_ROOT/scripts/luisalejandro.org/output`. This is the **generated** Cosmic file, not an `input/` Gemini template.

## Frontmatter (pre-publish)

`parseGeneratedFile` requires a YAML block between `---` fences. Use this shape:

```yaml
---
generated_at: '2026-08-15T23:00:00.000Z'
source_file: extract.ts
post_id: null
published: false
hero: images/voice-corpus-extractor-hero.jpg
teaser: >-
  Short SEO excerpt, max 155 characters, Spanish, with a verb and a payoff.
categories:
  - Desarrollo de Software
title: Action-oriented title, max 100 characters, no trailing period
slug: action-oriented-title-max-100-characters-no-trailing-period
voice_author: luisalejandro
---
```

| Field | Rule |
| --- | --- |
| `generated_at` | ISO-8601 UTC now |
| `source_file` | Basename of the primary code file, or `cursor-skill` |
| `post_id` | Always `null` until `blog-post` writes an id |
| `published` | Always `false` until Cosmic upload (the poster sets it) |
| `hero` | `images/<file>.jpg` relative to the output dir |
| `teaser` | ≤ 155 characters |
| `categories` | One existing name |
| `title` | ≤ 100 characters |
| `slug` | From title, rules below |
| `voice_author` | `luisalejandro` |

Do not set `post_id` or `published: true` yourself.

### Slug

Same as `generateSlug` in frontdesk `scripts/luisalejandro.org/shared.ts`:

1. Lowercase
2. NFD normalize; strip combining marks (accents)
3. Drop characters other than word chars (`[A-Za-z0-9_]`), space, hyphen
4. Spaces → `-`; collapse `--`; trim leading/trailing `-`

Example: `Limpia tu buzón: Crea un script` → `limpia-tu-buzon-crea-un-script`

## Body structure

1. **No title heading.** First line after frontmatter is the first sentence of the intro.
2. **Intro:** 2–4 sentences. Problem-first, personal `yo`, then what you will show.
3. **Sections:** numbered `### 1. …`, `### 2. …`. Not `##`. Not unnumbered H2 essays.
4. **Footer** — exact, including the rule; nothing after it:

```markdown
---
Otros proyectos en [mi perfil de GitHub](https://github.com/LuisAlejandro).
```

## Voice

Persona: @LuisAlejandro, senior engineer talking to a peer.

- Spanish (Venezuela), informal **tú**, imperative (`Usa`, `Añade`, `Evita`)
- English tech terms stay English, often in backticks
- Direct, pragmatic, a little energetic — not academic, not corporate
- Explain *why* in one beat, then show the code
- When showing a pitfall: `✅ **Correcto:**` / `❌ **Incorrecto:**` immediately before the example

## Technical density

Runnable code in the article comes from the gist (`GIST_URL` / `FILES`), not from a second invented copy.

- Link `GIST_URL` in the intro or `### 1.`
- The clone `bash` fence must match the handoff `CLONE` line exactly
- Every runnable fence is a named gist file: first line comment or a short prose label (`extract.ts`), then a verbatim excerpt (full file or a contiguous slice)
- Clone/run steps in prose must match gist `README.md` (install, env, command names)
- `❌ Incorrecto` pitfalls may be original (they are not the working example)
- Pseudocode is allowed to name an algorithm the listing would bury
- Markdown tables only when comparing options

Do not pad to a word count. Typical useful length is 800–1800 words; stop when the problem is solved.

Do not invent runnable snippets that are not in the gist.

## Images

**Pre-publish (what you write):** markdown images. `blog-post` uploads `images/` and rewrites them to Cosmic figure HTML.

```markdown
![A three-stage pipeline: download corpus, extract voice profile, write markdown.](images/voice-extract-pipeline.jpg)
```

Hero lives only in frontmatter (`hero: images/...`), not as a duplicate in the body.

**After publish** (existing output files): `<span class="figure figure-right-40" data-figure-src="…" data-figure-href="…" data-figure-alt="…"></span>`. Do not author that HTML in a new post.

Mermaid: not the primary published diagram. Add a mermaid fence only if the user asks for it in the source file as an extra.

## Links

Required: one markdown link to `GIST_URL` (no raw gist URL). Optional extras: 1–2 external docs plus an internal `https://luisalejandro.org/blog/...` link when a related post exists. Do not invent internal slugs.

## Out of scope for the body

- H1 / unnumbered `##` section titles
- Explicit FAQ heading
- Gemini `input/` frontmatter (`post_type`, `premise`, `processed`)
- Secrets, credentials, private customer data
