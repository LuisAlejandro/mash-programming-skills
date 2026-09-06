# Grounding the interview in the repo

Required read at the start of Phase 0, before the repo model is built.

Read `rosey/foundation/STRATEGY.md` with the native file-read tool. When it exists, note its shape: it may be this skill's house format, a Wondelai-written file (carrying `Diagnosis`, `Guiding Policy`, `Coherent Actions`, `No-List`, `Strategy Canvas & ERRC Grid`, `Beachhead`, `Whole-Product Checklist` — written first by the business metaskills), or a hand-written/multi-writer doc. Read it by meaning regardless of shape; `references/update-run.md` owns how each shape is edited.

Then read the **Wondelai foundation files** in `rosey/foundation/` when they exist — `CUSTOMER.md`, `POSITIONING.md`, `OFFER.md`, `METRICS.md`, `PRODUCT.md` — as canonical grounding for the concepts they own. These are the deep, dedicated files the business metaskills write; `rosey/foundation/STRATEGY.md` carries only thin pointers to them. Read them by meaning: `CUSTOMER.md` grounds the Users section (job statement, segments, best-fit customer), `POSITIONING.md` grounds Positioning (one-liner, market category, key messages), `OFFER.md` grounds the offer/pricing context, `METRICS.md` grounds Key metrics, and `PRODUCT.md` grounds the product's vision and MVP definition. Where a foundation file exists, seed the corresponding section from it and let the user confirm or correct — do not re-ask what the file already answers.

Then build a **repo model** - your working understanding of what this product is - from two inputs with different jobs:

- **What the product is.** Stated intent (README, `docs/`, an existing `rosey/foundation/STRATEGY.md`, and the `rosey/foundation/PRODUCT.md` foundation file) and structure (what the code is organized around, what is public, what is tested) - the authority for the problem, approach, and persona questions. Bound the read to "what is this and who is it for"; do not profile the whole repo.
- **What is getting attention now.** Recent commits or PRs, informing only the Tracks question and staleness in an update run. A burst of recent work is a fact about the last few weeks, not about what the product is; where it disagrees with stated intent, that is a question for the user ("recent work is mostly in X - is X a track, a temporary push, or unrelated?"), never a conclusion.

If the repo has no substantive content, say so in one line and run the interview ungrounded - a normal path, not a blocker.

Show the repo model in chat before the first question: three to five lines on what you take the product to be, who it seems to serve, and where attention has gone, each with its source named. Invite correction. On a first run the interview then runs in full; an update run still revisits only the section Phase 2 settles on. If it could not supply the product's name, ask for that here - the template's frontmatter and title need it.

## Focus hint

(Also stated in the always-loaded body, which is where it has to fire.) Any argument this skill was invoked with — present in the current prompt or conversation, from the user or a calling skill — is a focus hint: a section to revisit (`metrics`, `positioning`, `tracks`; older names such as `approach` or `who it's for` map to the current section) or a scope hint. With none, proceed open-ended and let the file state decide the path.
