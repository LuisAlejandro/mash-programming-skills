# Grounding Scout — sub-agent prompt

Seed a generic sub-agent with the prompt below, substituting `{topic}` and `{dossier-path}`. This is an **extraction** task: quote what the repo says, do not interpret or propose.

---

Gather grounding for a requirements brainstorm about **{topic}** in this repository.

Search first with the native file-search and content-search tools, then read targeted sections. Budget roughly 20 reads, preferring line ranges over whole files.

Find:

- whether something similar already exists;
- the most relevant existing artifacts (brainstorms, plans, specs, feature docs);
- adjacent examples of similar behavior worth imitating;
- the current state of anything the topic would touch — tables, routes, config, dependencies, model definitions.

Write a **grounding dossier** to `{dossier-path}`: at most 150 lines of verbatim quotes and short code snippets, each carrying a `file:line` pointer. Extraction only. If the topic has little footprint in this repo, write less rather than padding — a short honest dossier is more useful than a long speculative one.

Pay particular attention to anything that would make an **absence claim** false. If the brainstorm is likely to assert that something does not exist, quote whatever bears on that.

Return only a **gist**: 3–5 lines summarizing what the dossier holds, plus its absolute path. Do not return the dossier contents.

---

## Consuming the result

Carry only the gist into the dialogue. When the conversation needs specifics the gist cannot answer — the user challenges a claim, an approach needs grounding, the Phase 2.6 verifier needs a starting point — read the dossier on demand. It is a condensed, verified quote-sheet, always cheaper than re-scanning raw files.

Downstream consumers receive the dossier **path**, not its contents.
