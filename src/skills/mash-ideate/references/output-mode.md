# Resolving the output mode

Required read at Phase 0.0, before anything writes or resumes an ideation artifact. Ideation documents are markdown. No config file is read.

#### 0.0 Resolve Output Mode

`OUTPUT_FORMAT` is `md`. The ideation doc is a `.md` file.

- `output:md`, and a plain-language request for markdown, are no-ops. Strip the token from the focus hint.
- `output:html` and any other format token are ignored. Remember to emit one line above the post-ideation menu: `Ignored output:<value> — ideation documents are markdown.`
- A remembered preference for HTML does not switch the file away from markdown.
- "Ideate on an HTML export feature" names the work, not the document format. Do not treat it as an output token.

**Token-parsing convention:** only literal-prefix flag tokens (`output:`, `mode:` where applicable) are consumed and stripped. Other `<word>:<word>` tokens — including conventional commit prefixes like `feat:`, `fix:`, `chore:` that may appear inside a focus hint — pass through verbatim.

**Defer loading the rendering reference.** The deliverable is written at Phase 4, so `references/ideation-sections.md` and `references/markdown-rendering.md` are only needed then. Load them at write time (see `references/post-ideation-workflow.md` §4.1).

#### 0.1 Check for Recent Ideation Work

Look in `<repo-root>/.mash/ideation/` for ideation documents (`*.md` or `*.html`) created within the last 30 days. This is a repo-mode convenience: when there is no git repository or `<repo-root>` fails to resolve, skip the scan and continue — do not fail the run before 0.3 classifies mode, since elsewhere and no-repo runs write to the scratch area and never touch `<repo-root>/.mash/ideation/`.

A prior doc is relevant when its topic, path, or subsystem overlaps the requested focus, or the request is open-ended and one obvious recent open doc exists. Issue-grounded and non-issue ideations are distinct topics — never offer to resume across that line.

If a relevant doc exists, ask whether to continue from it or start fresh. If continuing: read it, summarize what has already been explored, and preserve the previous ideas and rejection summary.

**Markdown resume** updates that `.md` file. **HTML resume** writes a new `.md` file beside it and leaves the HTML file in place. There is no HTML renderer.
