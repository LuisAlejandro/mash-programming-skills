# Contributing Baseline

Generate `CONTRIBUTING.md` or `CONTRIBUTING.rst` for open-source repos using this shared structure. Keep the text very similar across repos; change only repo-specific names, URLs, commands, package layout, and test instructions.

## Required Sections

1. **Contributing**
   - Welcome contributors.
   - Say contributions are appreciated and credit is given.

2. **Types of Contributions**
   - Report bugs.
   - Fix bugs.
   - Implement features.
   - Improve documentation.
   - Submit feedback.

3. **Report Bugs**
   - Link to `https://github.com/LuisAlejandro/<repo_name>/issues`.
   - Ask for OS/version, setup details, logs, and reproduction steps.

4. **Suggest Features**
   - Ask contributors to describe the problem, proposed behavior, alternatives, and scope.

5. **Local Development**
   - Fork and clone the repo.
   - Create a branch from `develop`.
   - Use the repo's existing setup path, preferring `make` targets and Docker workflow when present.
   - Mention `make console` when the repo uses Docker for interactive commands.

6. **Quality Checks**
   - Prefer `make lint` and `make test` when those targets exist.
   - If repo-specific commands are required, include them under the same section.

7. **Pull Request Guidelines**
   - Include tests for behavior changes.
   - Update docs when user-facing behavior changes.
   - Keep scope focused.
   - Link related issues.

8. **Maintainer Notes**
   - Mention that releases are handled by maintainers.
   - Do not ask contributors to publish packages or push tags.

## Style

- Use the same documentation format as the repo: RST for RST repos, Markdown for Markdown repos.
- Keep prose concise and friendly.
- Avoid duplicating long architecture docs; link or summarize repo-specific details.
- Do not include secrets or private contact information.
