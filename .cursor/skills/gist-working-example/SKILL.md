---
name: gist-working-example
description: >-
  Builds a minimal, secret-free, cloneable GitHub gist with a working example
  distilled from source code in the current workspace (README plus flat files).
  Asks before creating a public gist via gh gist create --public. Use when the
  user wants a reproducible gist, a cloneable example for a blog post, or when
  write-technical-article needs a gist before drafting.
---

# Gist Working Example

Personal skill. Invoke by name, or execute when `write-technical-article` says to read this file. Creates a **public** gist only after the user confirms. Default `gh gist create` is secret — this flow **must** pass `--public`.

Do **not** create a GitHub repo. Do **not** run `gh gist edit` (new gist per article). Do **not** invent a gist URL if `gh` fails.

## Workflow

```
- [ ] 1. Read named source code
- [ ] 2. Design a flat, runnable file set
- [ ] 3. Write files to a temp dir (no secrets)
- [ ] 4. Ask before creating a public gist (stop until the user answers)
- [ ] 5. If yes: gh gist create --public; print handoff block
```

### 1. Topic and sources

Collect topic + source paths from the user or the calling skill. Read that code. **Do not invent APIs, flags, or behavior.**

Strip secrets: tokens, passwords, `.env` values, Cosmic keys, private URLs, customer data.

### 2. Minimal flat extract

Gists have **no directories**. Everything lives at gist root.

Keep the slice small enough to run after clone:

- `README.md` (required) — Spanish, same peer voice as the blog: what it is, clone, run, env
- One or few source files (the teachable core, not the whole app)
- `.env.example` only if the example needs env vars (placeholders, never real keys)
- Tiny `package.json` / one install command only if stdlib is not enough

Forbidden in the gist: `node_modules`, nested paths, product-only internals the reader cannot run, real credentials.

Prefer rewriting imports so files work at gist root. If that would lie about the original API, stop and ask.

### 3. Temp dir

```bash
work="$(mktemp -d /tmp/gist-working-example.XXXXXX)"
```

Write files there. In `README.md`, tell the reader to clone from the gist page. Do not invent an id. The exact `git clone https://gist.github.com/<id>.git` line belongs in the handoff block (and in the article), after create.

### 4. Ask gate (hard)

Show the user:

- Proposed `gh gist create` `--desc` (one line)
- File list and one-line purpose each
- Explicit: **this gist will be public**, listed, and **cannot be converted back to secret**

**Ask** whether to create it.

- **No:** stop. Print `GIST_URL:` empty. The caller must **not** write the article.
- **Yes:** continue. Never create before this answer.

### 5. Create

Check `gh` first. If missing or not authenticated for gists, stop and report `gh auth status`. Do not invent a URL.

From `$work`:

```bash
gh gist create --public -d "<desc>" README.md <other files...>
```

`--public` is required. Capture the printed URL (e.g. `https://gist.github.com/<user>/<id>`). Parse `<id>` from the last path segment. Do not run `gh gist edit`.

### 6. Handoff (required)

Print exactly this block (no extra keys):

```text
GIST_URL: https://gist.github.com/<user>/<id>
GIST_ID: <id>
CLONE: git clone https://gist.github.com/<id>.git
FILES: README.md, <file>, …
```

`FILES` is a comma-separated list of gist filenames.

## Hard rules

- Never `gh gist create` without `--public` in this skill
- Never `gh gist create` without the ask
- Never a GitHub repository instead of a gist
- Never host `curl` to gist.github.com as a create path
- Fail closed on `gh` errors

## Caller: write-technical-article

When this skill is run as a subroutine, the caller waits for the handoff block. Empty `GIST_URL` means abort the article.
