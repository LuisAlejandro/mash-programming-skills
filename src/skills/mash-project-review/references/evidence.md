# Evidence

Mirror the mash-work handoff. The report and the chat handoff carry the same blocks. One block per failed automated check and per blocked automated check. A `Pass` row may instead keep a single line with the command and the exit code.

```text
MASH_EVIDENCE
$ <exact command>
<verbatim stdout or stderr — not a paraphrase>
END_MASH_EVIDENCE
```

Rules:

- Name the command, then paste its real output. "The scan failed" is not evidence. A command with an empty body is not evidence.
- Paste the portion that shows the finding (the axe rule object, the ZAP alert, the audit advisory). When the full log is long, paste that excerpt verbatim and say the rest stayed in the run temp directory. Do not summarize the excerpt.
- The temp directory is the one created in Phase 0. Do not commit it. Do not copy a raw scanner file into the repo. Inline the redacted excerpt in the report.
- Use repo-relative paths if a path must appear. Absolute paths and home directories do not belong in the report.

## Redaction

Before the block is written, replace any of the following with `[redacted]`:

- `Authorization` and `Proxy-Authorization` header values
- `Cookie` and `Set-Cookie` header values
- Query or body fields named `token`, `access_token`, `refresh_token`, `id_token`, `password`, `secret`, `api_key`, or `apikey`
- A `Bearer` credential
- Session identifiers, magic links, and one-time codes

If the command line itself contained a secret, record the same argv with the secret replaced. Do not write the original command into the report and then delete it from chat only.

HTML captures can contain account data. Keep them in temp. The evidence block gets rule ids, selectors, and alert names, not a dump of the document.
