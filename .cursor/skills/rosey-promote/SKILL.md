---
name: rosey-promote
description: "Draft launch or promotion copy for a shipped feature."
disable-model-invocation: true
argument-hint: "[optional: what shipped and/or channels, e.g. 'a tweet thread and a LinkedIn post']"
---

# Promotion Copy

Turn a feature that just shipped into copy-pasteable, user-facing announcement copy, right inside the engineering workflow — so the messaging doesn't wait for a separate marketing pass.

**Done when:** every drafted channel is presented as a labeled, copy-pasteable block and the user has been offered a revision. **This skill drafts only — it never posts, publishes, schedules, commits, or opens PRs.** Posting is a human action.

## Phase 1 — Figure out what shipped

A free-form description in the arguments is the source of truth. Otherwise derive it from context, using what's available and blocking on no single source:

- **Merged/active PR** — `gh pr view --json title,body,url` (the title and body usually state the user-facing value)
- **The diff** — `git diff main...HEAD --stat`, skimming notable changes so the claim is grounded in what actually changed
- **Changelog** — the top or `[Unreleased]` entry in `CHANGELOG.md` or `CHANGELOG.rst`
- **Recent commits** — `git log --oneline -15` for the arc of the change

Then write a 1-3 sentence summary of the **user-facing value**: what a user can now do that they couldn't before, and why they'd care. Outcome, not implementation — "You can now export any report to CSV in one click", not "Added a CsvSerializer and an export endpoint." If you can't confidently tell what shipped, ask one short question rather than guessing.

## Phase 2 — Pick channels

Default to an X post (or short thread) plus a one-line changelog / release blurb. If the user named channels — LinkedIn, email, a blog intro, a demo script — draft those instead of or in addition to the defaults. Scale to the change: a small fix warrants one or two short drafts, a flagship feature a cross-channel set. Don't force a fixed template.

## Phase 3 — Draft the copy

Draft directly from the editorial and social fundamentals below. No external tooling is involved.

### Path B — Direct drafting

**Every channel:**

- Lead with the user-facing outcome — what someone can now do, not how it was built.
- One idea per piece. Cut windup, hedges, and throat-clearing.
- Plain, active language. Strip AI tells: "thrilled/excited to announce", "game-changer", "in today's fast-paced world", "unlock/leverage/seamless", em-dash padding.
- Read it back as if saying it to one user. If a person wouldn't say it, rewrite it.

**Distributed channels:** the first line is the hook and has to earn the next line (feeds truncate) — no preamble. Match each channel's native shape and length; never reuse one draft verbatim across channels. One clear CTA where the channel supports it. Hashtags 0-2, and only where the channel expects them.

**Per channel:**

- **X** — value in the first line; ~1-3 tight lines. Thread only when there's more than one beat worth its own line.
- **Changelog / release blurb** — one declarative line naming the new capability. Plain, not promotional.
- **LinkedIn** — a short paragraph: human angle (why it matters), then the what. Warmer than X.
- **Email** — benefit-stating subject + 2-4 sentence body + one CTA.
- **Blog intro** — one opening paragraph framing the problem and the new capability; leave the deep-dive to the author.
- **Demo script** — 3-6 spoken beats: hook, problem, action, payoff.

One strong draft per channel by default; produce more only when asked ("3 tweet options"), capped at ~3.

## Phase 4 — Present the drafts

Show every draft as a clean, copy-pasteable block labeled by channel:

```
### X post
<the copy>
```

Offer to revise (tone, length, angle, more variations, another channel). **Do not post, publish, schedule, commit, or open a PR** — end by reminding the user the drafts are theirs to ship.
