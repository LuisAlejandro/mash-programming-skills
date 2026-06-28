---
name: rosey-design-system
description: Creates an OpenDesign design-system package by seeding an agent-managed OpenDesign draft from root DESIGN.md. Phase 0 creates or improves root DESIGN.md from the implemented frontend, then later phases create a draft, open its workspace, run workspace generation, optionally revise, publish, copy the generated workspace package to rosey/design-system, and write an async manifest.
---

# Create OpenDesign Design System Package

## Communication while using this skill

**Caveman full** for assistant status prose while this skill runs: drop articles, use fragments when clear, prefer short synonyms, and keep technical terms exact. Technical accuracy unchanged; quoted errors, code, API payloads, and command output unchanged. Drop full for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, required input questions, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman full applies to chat and status prose, not copied `DESIGN.md` content, async manifests, daemon responses, generated package metadata, or validation output.

## Overview

Use this skill to create the OpenDesign design-system package that becomes input for `rosey-design-catalog`.

The workflow first ensures the source folder has a high-quality root `DESIGN.md`. Phase 0 always runs: when `DESIGN.md` exists, improve it for accuracy, specificity, and missing sections; when it does not exist, generate it from the implemented frontend using [`phase-0-extract-design-system.md`](phase-0-extract-design-system.md). Phase 1 and later always receive that `DESIGN.md`, create an OpenDesign draft with the root `DESIGN.md` as `body`, open the agent-managed design-system workspace, run workspace generation through OpenDesign `/api/runs`, audit the package through the daemon endpoint, optionally apply one revision, publish the draft, copy the generated workspace package to `rosey/design-system`, and write an async manifest. `rosey-design-catalog` may run later and auto-discover `rosey/design-system/DESIGN.md`.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. May ask blocking questions for optional inputs.
- `mode:non-interactive` — scripted or consumer execution (for example DesignCandidates bootstrap). No blocking questions; use conservative defaults for optional inputs.

Strip the mode token before resolving inputs. If no mode token is present, set `INTERACTION_MODE=interactive`.

When `INTERACTION_MODE=non-interactive`:

- Do not use blocking question tools or wait for user confirmation.
- Skip optional revision offers unless `revisionFeedback` is already provided.
- Proceed through publish, copy to `rosey/design-system`, and manifest write without prompts.

## Inputs

Ask for or infer:

- `sourceDir`: optional absolute path to a local folder. When omitted, use the current workspace root folder. Phase 0 always creates or improves root `DESIGN.md` here before OpenDesign draft creation.
- `appRoot`: optional frontend app directory for Phase 0 when the UI is nested.
- `focus`: optional Phase 0 area to improve, such as tokens, components, accessibility, or responsive behavior.
- `name`: optional display name for the OpenDesign design system.
- `summary`: optional short product summary for OpenDesign metadata. Default: infer from `DESIGN.md` or README.
- `sourceNotes`: optional instructions or evidence notes for the OpenDesign workspace agent. Default: tell OpenDesign to preserve and expand the prepared root `DESIGN.md`.
- `provenanceNotes`: optional additional provenance notes for OpenDesign metadata.
- `revisionFeedback`: optional feedback to apply after draft creation.
- `sectionTitle`: optional target section for revision feedback.
- `agentId`: optional workspace generation agent. Default: `opencode`. Do not switch to Claude or Cursor unless the user explicitly requests that agent.
- `opencodeConfig`: optional OpenCode config path. Default: `~/.config/opencode/opencode.json`. Required when `agentId` is `opencode`.
- `daemontUrl`: optional, default `http://127.0.0.1:7456`.
- `openDesignProjectRoot`: optional, used to resolve `.od` when `OD_DATA_DIR` is unset.

## Workflow

### 0. Hindsight Gate

Before release work:

1. Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md).
2. Run `hindsight-embed daemon status` (see [`rosey-hindsight`](../rosey-hindsight/SKILL.md)).
3. If available, recall design-system context for the current repo.
4. If unavailable, record `HINDSIGHT: unavailable` in the handoff.

### Phase 0: Create Or Improve `DESIGN.md`

Resolve `SOURCE_DIR` first:

```bash
SOURCE_DIR="${SOURCE_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)}"
test "${SOURCE_DIR#/}" != "$SOURCE_DIR"
test -d "$SOURCE_DIR"
```

Run the full extraction workflow in [`phase-0-extract-design-system.md`](phase-0-extract-design-system.md) with `outputPath` fixed to `$SOURCE_DIR/DESIGN.md`.

- If `$SOURCE_DIR/DESIGN.md` already exists, Phase 0 improves it: make it more accurate, specific, complete, and grounded in current code. Preserve good existing content, but remove stale or generic claims.
- If `$SOURCE_DIR/DESIGN.md` does not exist, Phase 0 creates it from the implemented frontend.
- Phase 0 must finish with `test -f "$SOURCE_DIR/DESIGN.md"`.
- Track whether Phase 0 `created` or `improved` the file for the handoff.

Do not rely on OpenDesign daemon generation as a substitute for Phase 0. Phase 1 always starts with a root `DESIGN.md` present.

### Phase 1: Validate Source And Daemon

When `sourceDir` is omitted, use the current workspace root folder. The resolved source must be an absolute directory with root `DESIGN.md` created or improved by Phase 0.

When `agentId` is `opencode` (default), configure global OpenCode permissions **before** starting or relying on the OpenDesign daemon. Headless `/api/runs` has no UI to approve `external_directory` prompts, so OpenCode auto-rejects them and the run can report `succeeded` with zero workspace writes. Merge allow rules into `~/.config/opencode/opencode.json` for the OpenDesign workspace data directory and `SOURCE_DIR`. Preserve any existing config keys; only add or update the `permission.external_directory` patterns this workflow needs.

The OpenDesign daemon must be running before any `curl "$DAEMON/api/..."` request can succeed. Run it like the desktop app does: outside the source repo and outside any linked git worktree. If the health check cannot reach the daemon, start it as a long-running process from a neutral non-git directory, wait for `http://127.0.0.1:7456` to listen, then retry the health check before moving to Phase 2. Do not run the daemon inline inside the validation script because it keeps running.

```bash
command -v curl >/dev/null
command -v jq >/dev/null
command -v rg >/dev/null

# OpenDesign CLI help shows `od design-systems ...`; on macOS `/usr/bin/od` is unrelated.
# Invoke the OpenDesign binary (`opendesign`); override with OPENDESIGN_CLI when needed.
OPENDESIGN_CLI="${OPENDESIGN_CLI:-opendesign}"
command -v "$OPENDESIGN_CLI" >/dev/null

SOURCE_DIR="${SOURCE_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)}"
test "${SOURCE_DIR#/}" != "$SOURCE_DIR"
test -d "$SOURCE_DIR"
test -f "$SOURCE_DIR/DESIGN.md"
echo "Source DESIGN.md: present; draft will use it"

AGENT_ID="${AGENT_ID:-opencode}"
if [ "$AGENT_ID" = "opencode" ]; then
  OPENCODE_CONFIG="${OPENCODE_CONFIG:-$HOME/.config/opencode/opencode.json}"
  mkdir -p "$(dirname "$OPENCODE_CONFIG")"
  if [ ! -f "$OPENCODE_CONFIG" ]; then
    echo '{"$schema":"https://opencode.ai/config.json"}' > "$OPENCODE_CONFIG"
  fi

  OPEN_DESIGN_DATA_DIR="${OPEN_DESIGN_DATA_DIR:-$HOME/Library/Application Support/Open Design/namespaces/release-stable/data}"

  tmp="$(mktemp)"
  jq \
    --arg od "$OPEN_DESIGN_DATA_DIR" \
    --arg src "$SOURCE_DIR" \
    '
      .["$schema"] //= "https://opencode.ai/config.json" |
      if (.permission | type) != "object" then .permission = {} else . end |
      .permission.external_directory //= {} |
      .permission.external_directory[($od + "/**")] = "allow" |
      .permission.external_directory[($src + "/**")] = "allow"
    ' "$OPENCODE_CONFIG" > "$tmp"
  mv "$tmp" "$OPENCODE_CONFIG"

  jq -e \
    --arg od "$OPEN_DESIGN_DATA_DIR" \
    --arg src "$SOURCE_DIR" \
    '
      ((.permission | type) == "object") and
      (.permission.external_directory[($od + "/**")] // "") == "allow" and
      (.permission.external_directory[($src + "/**")] // "") == "allow"
    ' "$OPENCODE_CONFIG" >/dev/null

  echo "OpenCode external_directory allow: $OPEN_DESIGN_DATA_DIR/** and $SOURCE_DIR/** ($OPENCODE_CONFIG)"
fi

DAEMON="${DAEMON:-http://127.0.0.1:7456}"
if ! curl -fsS --max-time 5 "$DAEMON/api/health" >/dev/null \
  && ! curl -fsS --max-time 5 "$DAEMON/api/design-systems" >/dev/null; then
  echo "OpenDesign daemon is not running. Start it outside this git repo, for example:" >&2
  echo "  (cd \"\${TMPDIR:-/tmp}\" && $OPENDESIGN_CLI --no-open)" >&2
  exit 1
fi
```

Do not create drafts from folders under OpenDesign desktop runtime data.

| Gate | What runs | Verified by |
| --- | --- | --- |
| 1 Draft creation | POST `/api/design-systems` | Created draft ID |
| 2 Project creation | POST `/api/design-systems/:id/workspace` | Workspace Project ID |
| 3 Setup context | POST `/api/projects/:id/files` | File created |
| 4 Generation run | POST `/api/runs` | Run status `succeeded` |
| 5 Quality audit | GET `/api/projects/:id/design-system-package-audit` | Audit OK |
| 6 Publish | PATCH `/api/design-systems/:id` | Published status |

### Phase 2: Create Seeded Draft

Use the daemon HTTP API to create an agent-managed OpenDesign draft. Seed `body` with the prepared root `DESIGN.md`; this preserves the repository-grounded design-system documentation instead of relying on daemon local import heuristics. Keep `summary` short and put instructions/evidence in `sourceNotes` or `provenance.notes`.

```bash
DAEMON="${DAEMON:-http://127.0.0.1:7456}"
DESIGN_SYSTEM_NAME="${DESIGN_SYSTEM_NAME:-$(basename "$SOURCE_DIR") Design System}"

if [ -z "${DESIGN_SYSTEM_SUMMARY:-}" ]; then
  DESIGN_SYSTEM_SUMMARY=$(
    awk '
      /^## / { in_section = ($0 ~ /^## (Overview|Product Context|Product|Brand|0\. Scope)/); next }
      in_section && NF {
        sub(/^[[:space:]-]+/, "")
        print
        exit
      }
    ' "$SOURCE_DIR/DESIGN.md"
  )
fi
DESIGN_SYSTEM_SUMMARY="${DESIGN_SYSTEM_SUMMARY:-Design system seeded from $SOURCE_DIR/DESIGN.md.}"

DESIGN_SYSTEM_SOURCE_NOTES="${DESIGN_SYSTEM_SOURCE_NOTES:-Existing root DESIGN.md is the canonical seed. Preserve its accurate codebase-grounded tokens, components, UX patterns, and implementation rules, then expand into a full OpenDesign package with README, SKILL.md, tokens, previews, source evidence, and ui_kits/app.}"
DESIGN_SYSTEM_PROVENANCE_NOTES="${DESIGN_SYSTEM_PROVENANCE_NOTES:-Goal: combine the accuracy of the existing repository-grounded DESIGN.md with the richer OpenDesign package generation.}"

DS=$(curl -fsS --max-time 30 -X POST "$DAEMON/api/design-systems" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n \
    --rawfile body "$SOURCE_DIR/DESIGN.md" \
    --arg title "$DESIGN_SYSTEM_NAME" \
    --arg summary "$DESIGN_SYSTEM_SUMMARY" \
    --arg sourceDir "$SOURCE_DIR" \
    --arg sourceNotes "$DESIGN_SYSTEM_SOURCE_NOTES" \
    --arg provenanceNotes "$DESIGN_SYSTEM_PROVENANCE_NOTES" \
    '{
      title: $title,
      summary: $summary,
      category: "Custom",
      surface: "web",
      status: "draft",
      artifactMode: "agent-managed",
      body: $body,
      sourceNotes: $sourceNotes,
      provenance: {
        localCodeFiles: [$sourceDir],
        notes: $provenanceNotes
      }
    }')" \
  | jq -r '.designSystem.id')

test -n "$DS"
test "$DS" != "null"
echo "Created seeded design-system draft: $DS"
```

### Phase 3: Open Workspace And Generate Package

Open the agent-managed design-system workspace. The workspace copies the seeded `DESIGN.md` into an OpenDesign project where the OpenDesign agent can build the richer package files. Workspace generation writes into the workspace project directory, not automatically into the user design-system package directory.

```bash
WORKSPACE=$(curl -fsS --max-time 30 -X POST "$DAEMON/api/design-systems/$DS/workspace" \
  -H 'Content-Type: application/json')

PROJECT_ID=$(echo "$WORKSPACE" | jq -r '.project.id // .projectId // empty')

test "$PROJECT_ID" != ""
echo "Opened design-system workspace project: $PROJECT_ID"

OPEN_DESIGN_DATA_DIR="${OPEN_DESIGN_DATA_DIR:-$HOME/Library/Application Support/Open Design/namespaces/release-stable/data}"
WORKSPACE_DIR="$OPEN_DESIGN_DATA_DIR/projects/$PROJECT_ID"
test -d "$WORKSPACE_DIR"
echo "Workspace package output directory: $WORKSPACE_DIR"
```

Create the setup source-context manifest before starting `/api/runs`. This mirrors the OpenDesign UI setup flow: write `context/source-context.md` into the project through the daemon project file endpoint, then make the agent read it first.

```bash
SOURCE_SLUG=$(
  basename "$SOURCE_DIR" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9._-][^a-z0-9._-]*/-/g; s/^-//; s/-$//'
)
SOURCE_SLUG="${SOURCE_SLUG:-source}"

SOURCE_CONTEXT=$(cat <<EOF
# Design System Source Context

This file is generated during setup and should be treated as source evidence for the design-system project. Use it before writing or revising DESIGN.md, previews, tokens, UI kit examples, or assets.

## Company / Product

Canonical design-system title: $DESIGN_SYSTEM_NAME

$DESIGN_SYSTEM_SUMMARY

## GitHub Repositories

- None linked.

Connector status: GitHub connector is not configured; repository intake will use local git credentials or authenticated GitHub CLI when possible.

## Local Code

Linked folders readable by the local agent:
- $SOURCE_DIR

### Local Folder Intake Runbook

Local folder intake is required before drafting from linked local code folders:
1. For each linked folder, run the bounded local intake command before writing design-system files:
   - \`"\$OD_NODE_BIN" "\$OD_BIN" tools connectors local-design-context --path '$SOURCE_DIR' --output context/local-code/$SOURCE_SLUG.md\`
2. The command selects design-system-relevant source files plus available logos/icons/fonts, writes a reviewable evidence note, and copies snapshots under \`context/local-code/\`.
3. Inspect the generated evidence note plus snapshots for README, package manifests, Tailwind/theme/token files, global CSS, font declarations, component source, layout shells, icons/logos/assets, and representative app entry files.
4. If the command cannot read a linked folder or write snapshots, stop and explain the local file access problem instead of inventing tokens from the folder name.

Copied browser-selected code snapshot files under \`context/local-code/\`: none.

## Design And Brand Resources

Figma files selected: none.

Locally parsed Figma summaries under \`context/figma/\`: none.

Fonts, logos, and assets selected: none.

Uploaded brand asset files under \`assets/\`: none.

## Notes

$DESIGN_SYSTEM_PROVENANCE_NOTES

## Review Contract

- \`/design-systems/create\` only collected setup inputs. All GitHub extraction, local evidence intake, source reading, design-system construction, package audit, and artifact writes should happen inside this project workspace.
- DESIGN.md is the canonical source of truth.
- Use the canonical design-system title above for headings, README/SKILL names, preview labels, and UI-kit copy unless inspected evidence proves a more accurate product name. Never title the system from URL protocol text such as \`https\`.
- colors_and_type.css should hold concrete reusable tokens when the source evidence supports them; if fonts/ contains preserved font files, colors_and_type.css must bind those files with @font-face, @import, or url(...) references so typography does not fall back to substitute fonts.
- README.md and SKILL.md should make the extracted system reusable as a real Open Design design-system package.
- README.md should include a source-backed Product Overview/Product Context section, source repository or source folder references, package contents, a concrete \`## Preview Manifest\` listing every generated \`preview/*.html\` card, and reuse workflow, similar to Claude Design exports.
- SKILL.md should include YAML frontmatter with \`name\`, \`description\`, and \`user-invocable\`, plus Claude-style reusable skill sections: What is inside, Source context, When to use this skill, How to use, and Design system highlights. The usage guidance should point agents at README.md, DESIGN.md, colors_and_type.css, preview/, assets/, build/, fonts/, source_examples/, and ui_kits/app/.
- README.md, SKILL.md, DESIGN.md, and ui_kits/app/README.md must describe the final focused preview cards and \`ui_kits/app/\` paths, not old scaffold names such as \`preview/typography-scale.html\` or \`ui_kits/generated_interface/\`.
- preview/ should contain small reviewable HTML cards for typography, color themes, spacing, radius, shadows, brand assets, and component evidence.
- source_examples/ or equivalent root/nested source files should preserve selected high-signal original components when snapshots include substantial app/component source, similar to Claude Design exports that keep files like SelectModelButton.tsx or ChatNavBar/index.tsx alongside the package. These examples should contain substantive original implementation code, not tiny stubs that only share the component name.
- ui_kits/app/ should contain an applied interface example, plus substantive role-based files under \`ui_kits/app/components/\` when the source snapshots include representative app shells, navigation, chat/input surfaces, or reusable components. \`ui_kits/app/README.md\` should explain structure, component files, usage, design notes, and source basis. \`ui_kits/app/index.html\` must load \`../../colors_and_type.css\`, must load/import/compose the modular component files, and must mount/render the composed interface instead of staying as a standalone generic static mock or disconnected script list. If the entry directly loads \`.jsx\`/\$.tsx\` files, include React, ReactDOM, and Babel standalone scripts and expose each loaded component as \`window.ComponentName\` / \`globalThis.ComponentName\`, or write compiled browser-ready JavaScript instead. For chat/workspace evidence, cover app shell, sidebar/navigation, assistant/list rail, chat area, input bar/composer, and message bubble/comment roles; the app shell component must compose those roles into one product-like surface. Placeholder component shells are not sufficient.
- Claude-style UI-kit entry contract:
  - When \`ui_kits/app/components/*.jsx\` or \`*.tsx\` files exist, \`ui_kits/app/index.html\` must behave like a runnable browser entry, not a static mock.
  - Use the same structure as Claude Design exports: load React, ReactDOM, and Babel standalone scripts, load \`../../colors_and_type.css\`, create a \`#root\`, load each component script from \`components/\`, then render the composed \`App\` component.
  - \`App.jsx\` must assign \`window.App = App\` (or \`globalThis.App = App\`), and every directly loaded component file must expose the same browser global for its component name.
  - Use this skeleton for direct JSX component kits, replacing the component list only when evidence supports different names:
    \`\`\`html
    <script src="https://unpkg.com/react@18.3.1/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js"></script>
    <link rel="stylesheet" href="../../colors_and_type.css">
    <div id="root"></div>
    <script type="text/babel" src="components/Sidebar.jsx"></script>
    <script type="text/babel" src="components/AssistantsList.jsx"></script>
    <script type="text/babel" src="components/ChatArea.jsx"></script>
    <script type="text/babel" src="components/MessageBubble.jsx"></script>
    <script type="text/babel" src="components/InputBar.jsx"></script>
    <script type="text/babel" src="components/App.jsx"></script>
    <script type="text/babel">
    const { App } = window;
    const root = ReactDOM.createRoot(document.getElementById('root'));
    root.render(<App />);
    </script>
    \`\`\`
- Preview cards and UI-kit visuals should explicitly label or model source-backed modules from the captured evidence instead of generic placeholder modules.
- assets/, build/, fonts/, and context/ should preserve logos, app icons, tray icons, installer/runtime icons, wordmarks, font files, provenance, and source notes for future projects.
- Claude-style build asset contract:
  - When evidence includes \`context/.../files/build/...\`, create a root \`build/\` directory and copy representative runtime assets there with their original filenames and path intent, such as \`build/icon.png\`, \`build/logo.png\`, \`build/tray_icon.png\`, and \`build/icon.ico\`.
  - Copy those runtime assets byte-for-byte from the captured \`context/.../files/...\` snapshots. Do not redraw, re-encode, optimize, or substitute generated placeholders for files that the evidence already captured.
  - Do not satisfy build/runtime icon evidence by only renaming those files into \`assets/\`. \`assets/\` may include convenience aliases, but root \`build/\` must preserve the source runtime files for future agents and package consumers.
  - \`preview/brand-assets.html\` should reference at least some real preserved files from \`build/\` or \`assets/\` with <img>, <picture>, <object>, or CSS \`url(...)\`, and README.md / SKILL.md should mention \`build/\` in the package manifest when it exists.
- preview/brand-assets.html should visibly reference preserved files from assets/ or build/ instead of recreating logos/icons as inline placeholder drawings.
- GitHub evidence must come from the bounded \`github-design-context\` command, not direct connector tree/content/raw tool calls. The command tries this-device git first, authenticated GitHub CLI second, and connector-platform fallback only when local access cannot read the repository.
- Linked local folder evidence should come from the bounded \`local-design-context\` command, which writes a local evidence note and snapshots under \`context/local-code/\` before final design-system rules are drafted.
- Before marking the design system ready, run \`"\$OD_NODE_BIN" "\$OD_BIN" tools connectors design-system-package-audit --path . --fail-on-warnings\` and fix every reported error or warning.
- Draft design systems cannot be used by other projects until published.

## Source Notes

$DESIGN_SYSTEM_SOURCE_NOTES
EOF
)

curl -fsS --max-time 30 -X POST "$DAEMON/api/projects/$PROJECT_ID/files" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n \
    --arg name "context/source-context.md" \
    --arg content "$SOURCE_CONTEXT" \
    '{name: $name, content: $content}')" \
  | jq -e '.file' >/dev/null

test -f "$WORKSPACE_DIR/context/source-context.md"
```

Run package generation before copying through the same `/api/runs` path used by the OpenDesign UI. Default to `opencode`; do not switch to Claude or Cursor unless the user explicitly requests that agent.

Phase 1 must merge `permission.external_directory` allow rules into `~/.config/opencode/opencode.json` before daemon startup when using `opencode`. Without those rules, headless `/api/runs` auto-rejects workspace and source-path access even when the run status is `succeeded`.

Also launch the OpenDesign daemon from a neutral non-git directory (desktop-app style), not from the linked source repo. The failure mode to guard is an empty successful run where OpenCode reports `external_directory ... auto-rejecting` in `events.jsonl`. If that happens after Phase 1 config enforcement, restart OpenDesign from a neutral directory, re-run Phase 1 to refresh allow patterns for the current `SOURCE_DIR`, and start a fresh `/api/runs` generation.

````bash
test -n "$WORKSPACE_DIR"
test -d "$WORKSPACE_DIR"
test -f "$WORKSPACE_DIR/DESIGN.md"

AGENT_ID="${AGENT_ID:-opencode}"
MODEL="${MODEL:-}"
SOURCE_DIR_SHELL_QUOTED=$(printf '%s' "$SOURCE_DIR" | jq -Rr @sh)

GENERATION_PROMPT=$(cat <<'EOF'
Create this project as a complete Open Design design system workspace.

Autonomy requirement:
- Do not ask setup or clarification questions during design-system generation.
- Do not emit `<question-form>`, "Quick brief — 30 seconds", direction cards, choice cards, or any UI that waits for user input.
- The setup page already collected the brief. If target surfaces, review priority, or workspace depth are missing, choose sensible defaults and begin generating the design-system artifacts immediately.

Project boundary:
- All GitHub extraction, local evidence intake, source reading, design-system construction, package audit, and final artifact writes must happen inside this project workspace and this project chat run.
- Treat `/design-systems/create` as setup only. Do not depend on that page for progress, review, or generated output; the project is the source of truth.

Use the files in this project as the design system source for future projects. Update `DESIGN.md` as the canonical rules document, and update supporting files when they make the system easier to review or reuse.

Expected output:
- A clear `DESIGN.md` with product context, visual foundations, color, type, spacing, layout, components, motion, voice, and anti-patterns.
- A Claude Design-quality package: `README.md`, `SKILL.md`, `colors_and_type.css`, provenance notes, `assets/`, `build/` when runtime icons exist, optional `fonts/`, category-specific `preview/` cards, and a reusable `ui_kits/app/` example.
- Write `README.md` as a reusable package guide, not only a generated file list. Include a source-backed Product Overview/Product Context section that explains what the product is, the primary UI surfaces, and the core capabilities evidenced by README/package/source files; include source repository or source folder references, package contents, preview manifest, and reuse workflow.
- README.md must include a concrete `## Preview Manifest` section that lists each generated `preview/*.html` card by exact path, what reviewers should inspect there, and which source-backed components, tokens, assets, or fonts it demonstrates. Keep this manifest synchronized with the actual `preview/` files.
- Preserve real source assets when evidence provides them: logos, app icons, tray icons, avatars, wordmarks, and font files belong in `assets/`, `build/`, or `fonts/`, not in prose-only notes. When source files include build/runtime icon assets such as installer icons, tray icons, app icons, or wordmarks under build/resources paths, preserve representative files under `build/` as Claude Design does. When multiple source logos/icons/fonts are captured, preserve a representative set instead of collapsing everything into one generic logo or font. If font files are preserved, bind them in `colors_and_type.css` with `@font-face`, `@import`, or `url(...)` references so previews and UI kits actually render the brand typeface.
Claude-style build asset contract:
- When evidence includes `context/.../files/build/...`, create a root `build/` directory and copy representative runtime assets there with their original filenames and path intent, such as `build/icon.png`, `build/logo.png`, `build/tray_icon.png`, and `build/icon.ico`.
- Copy those runtime assets byte-for-byte from the captured `context/.../files/...` snapshots. Do not redraw, re-encode, optimize, or substitute generated placeholders for files that the evidence already captured.
- Do not satisfy build/runtime icon evidence by only renaming those files into `assets/`. `assets/` may include convenience aliases, but root `build/` must preserve the source runtime files for future agents and package consumers.
- `preview/brand-assets.html` should reference at least some real preserved files from `build/` or `assets/` with `<img>`, `<picture>`, `<object>`, or CSS `url(...)`, and README.md / SKILL.md should mention `build/` in the package manifest when it exists.
- Preserve high-signal source component examples when evidence provides substantial app/component code. Copy at least a few real, substantive source-backed examples outside `context/` (for example `source_examples/SelectModelButton.tsx`, `source_examples/ChatNavBar/index.tsx`, or root/nested TSX files) so future agents can inspect the original implementation patterns without digging through intake snapshots. Do not replace captured source examples with tiny filename-only stubs.
- Split review previews into focused cards instead of one generic page. Prefer cards such as `preview/colors-primary.html`, `preview/colors-theme-light.html`, `preview/colors-theme-dark.html`, `preview/typography-specimens.html`, `preview/spacing-tokens.html`, `preview/spacing-radius.html`, `preview/spacing-shadows.html`, `preview/components-buttons.html`, `preview/components-inputs.html`, and `preview/brand-assets.html` when evidence supports them. `preview/brand-assets.html` must visibly load the preserved files from `assets/` or `build/` with real `img`, `picture`, `object`, or CSS `url(...)` references; do not redraw brand marks as inline placeholders when source assets were captured.
- Write `SKILL.md` as an agent-usable Claude Design-style skill entry, not only a loose Markdown note. Include YAML frontmatter with `name`, `description`, and `user-invocable`, then include reusable sections for `What is inside`, `Source context`, `When to use this skill`, `How to use`, and `Design system highlights`. Those sections should tell future agents to read README.md, DESIGN.md, colors_and_type.css, preview/, assets/, build/, fonts/, source_examples/, and ui_kits/app/ before generating artifacts.
- Build `ui_kits/app/` as an applied interface kit with `index.html`, a reusable README, and modular component files when the evidence includes representative product surfaces. `ui_kits/app/README.md` should document the kit structure, component files, usage workflow, design notes, and source basis, not only say the kit exists. `ui_kits/app/index.html` must load `../../colors_and_type.css`, must load/import/compose the modular component files under `ui_kits/app/components/`, and must mount/render the composed interface into the page; if it directly loads `.jsx`/`.tsx` files, include React, ReactDOM, and Babel standalone scripts and expose each loaded component as `window.ComponentName` / `globalThis.ComponentName`, or write compiled browser-ready JavaScript instead. Do not leave the entry page as a standalone generic static mock or disconnected script list when component files exist. For chat/workspace evidence, include substantive role-based components under `ui_kits/app/components/`: `App.jsx`, `Sidebar.jsx`, a list/rail component such as `AssistantsList.jsx`, a main workspace component such as `ChatArea.jsx`, an input/composer such as `InputBar.jsx`, and a message/comment component such as `MessageBubble.jsx`; the app shell component must compose the role components into one product-like surface; do not write one-line placeholder components.
Claude-style UI-kit entry contract:
- When `ui_kits/app/components/*.jsx` or `*.tsx` files exist, `ui_kits/app/index.html` must behave like a runnable browser entry, not a static mock.
- Use the same structure as Claude Design exports: load React, ReactDOM, and Babel standalone scripts, load `../../colors_and_type.css\`, create a `#root`, load each component script from `components/`, then render the composed `App` component.
- `App.jsx` must assign `window.App = App` (or `globalThis.App = App`), and every directly loaded component file must expose the same browser global for its component name.
- Use this skeleton for direct JSX component kits, replacing the component list only when evidence supports different names:
```html
<script src="https://unpkg.com/react@18.3.1/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js"></script>
<link rel="stylesheet" href="../../colors_and_type.css">
<div id="root"></div>
<script type="text/babel" src="components/Sidebar.jsx"></script>
<script type="text/babel" src="components/AssistantsList.jsx"></script>
<script type="text/babel" src="components/ChatArea.jsx"></script>
<script type="text/babel" src="components/MessageBubble.jsx"></script>
<script type="text/babel" src="components/InputBar.jsx"></script>
<script type="text/babel" src="components/App.jsx"></script>
<script type="text/babel">
const { App } = window;
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
</script>
```
- Preview cards and UI-kit visuals should name or model high-signal source components from the evidence, such as the captured sidebar, chat, composer, message, artifact, modal, avatar, or selector files. Avoid anonymous generic examples when concrete source component names are available.
- If older scaffold names exist (`preview/colors-node-types.html`, `preview/colors-ui-palette.html`, `preview/typography-scale.html`, `preview/spacing-system.html`, `preview/logo-variants.html`, or `ui_kits/generated_interface/`), replace them with the focused Claude-style structure above instead of extending the old generic files.
- Keep `README.md`, `SKILL.md`, `DESIGN.md`, and `ui_kits/app/README.md` in sync with the final file structure; do not leave manifest text pointing to older preview names or `ui_kits/generated_interface/`.
- Reviewable previews must appear in the right-side `Design System` tab and show real modules with preview cards, not a standalone marketing page or a single placeholder panel.

Core execution order:
1. Read `context/source-context.md` first, then run every intake command it lists for linked GitHub repositories and linked local code folders before editing design-system files.
2. Do not write `DESIGN.md`, token files, previews, UI-kit examples, or asset notes from URL text alone. When GitHub, local code, Figma, or assets were provided, preserve concrete evidence under `context/` and use it as the basis for the design-system files.
3. Before writing the design-system files, inventory the local evidence for product identity, real color/theme tokens, font families, brand assets, app shell layout, navigation, chat/input surfaces, and reusable components. Use this inventory to avoid generic tokens.
4. Copy high-signal source component examples from the snapshots when they explain the design system better than prose alone. Keep these examples outside `context/` as reusable package artifacts, not only as hidden evidence.
5. After evidence is collected, update the project files directly and keep the `Design System` tab reviewable.

Completion gate:
- For each linked GitHub repository, there must be a `context/github/*.md` evidence note plus command-written snapshots under `context/github/*/files/` before writing final design-system rules or previews. The snapshots should include theme/token/source files and any available binary assets or fonts selected by the intake command.
- For each linked local code folder, run the listed `local-design-context` command and use its `context/local-code/*.md` evidence note plus command-written snapshots under `context/local-code/*/files/` before writing final design-system rules or previews. Browser-copied snapshots already under `context/local-code/` are also valid local evidence.
- Do not call GitHub connector tree/content/raw tools directly from the agent. Use only the bounded `github-design-context` command listed in `context/source-context.md`; it tries this-device git first, authenticated GitHub CLI second, then connector-platform fallback when local access cannot read the repository.
- If the bounded command records `Read method: git-clone`, treat those this-device snapshots as the primary evidence. If it records `Read method: connector`, treat the connector-platform snapshots as valid fallback evidence and continue.
- For private repositories, local git credentials or GitHub CLI authentication (`gh auth login --web`) are preferred intake paths because the command still writes local evidence snapshots.
- If the bounded command cannot write snapshots at all, stop with the permission, GitHub CLI login, connection, rate-limit, or clone issue. Do not substitute ad-hoc public GitHub browsing, memory, or URL-only inference.
- Finish only after the project contains reviewable design-system artifacts: `DESIGN.md`, `README.md`, `SKILL.md`, reusable token/style files, focused preview HTML cards, UI-kit examples, preserved assets/fonts when supported, and provenance/context notes.
- Before your final response, run `"$OD_NODE_BIN" "$OD_BIN" tools connectors design-system-package-audit --path . --fail-on-warnings`. Fix every audit error and design-quality warning, including generic visual artifacts, thin source-backed modules, stale manifest paths, and missing representative assets/fonts. If an issue cannot be fixed because source evidence is missing, explain that blocker instead of claiming the design system is ready.
EOF
)

GENERATION_PROMPT=$(printf '%s\n\nDesign system workspace title:\n%s\n\nUse this title for README.md, SKILL.md, DESIGN.md, preview labels, and ui_kits/app copy unless the inspected source evidence proves a better product name. Do not derive the title from URL protocol text such as `https`.\n\nCompany / design system context:\n%s\n\nSource context manifest:\n- Read `context/source-context.md` before drafting. It records GitHub access readiness, local folder links, copied code snapshots, uploaded resources, and the review contract for this design system project.\n\nProvided resources:\n%s\n\nRead the linked local code folders that Open Design attached to this project: %s. Treat them as source context only unless the user asks you to edit them.\n\nLocal folder intake is required before drafting from linked local code folders:\n1. For each linked folder, run the bounded local intake command before writing design-system files:\n   - `"$OD_NODE_BIN" "$OD_BIN" tools connectors local-design-context --path %s --output context/local-code/%s.md`\n2. The command selects design-system-relevant source files plus available logos/icons/fonts, writes a reviewable evidence note, and copies snapshots under `context/local-code/`.\n3. Inspect the generated evidence note plus snapshots for README, package manifests, Tailwind/theme/token files, global CSS, font declarations, component source, layout shells, icons/logos/assets, and representative app entry files.\n4. If the command cannot read a linked folder or write snapshots, stop and explain the local file access problem instead of inventing tokens from the folder name.\n\nUse local code context to infer actual tokens, typography, spacing, components, assets, naming, and product surface patterns.\n\nKeep this scoped to the design-system project. When finished, summarize which files should be reviewed first.' \
  "$GENERATION_PROMPT" \
  "$DESIGN_SYSTEM_NAME" \
  "$DESIGN_SYSTEM_SUMMARY" \
  "$DESIGN_SYSTEM_SOURCE_NOTES" \
  "$SOURCE_DIR" \
  "$SOURCE_DIR_SHELL_QUOTED" \
  "$SOURCE_SLUG")

RUN_BODY=$(jq -n \
  --arg projectId "$PROJECT_ID" \
  --arg agentId "$AGENT_ID" \
  --arg message "$GENERATION_PROMPT" \
  --arg model "$MODEL" \
  '{
    projectId: $projectId,
    agentId: $agentId,
    message: $message,
    currentPrompt: $message,
    clientRequestId: ("rosey-design-system-" + (now | tostring))
  } + (if $model == "" then {} else {model: $model} end)')

RUN_ID=$(curl -fsS --max-time 30 -X POST "$DAEMON/api/runs" \
  -H 'Content-Type: application/json' \
  -H 'X-OD-Client: web' \
  -d "$RUN_BODY" \
  | jq -r '.runId')

test -n "$RUN_ID"
test "$RUN_ID" != "null"
echo "Started workspace generation run: $RUN_ID"

OPEN_DESIGN_DATA_DIR="${OPEN_DESIGN_DATA_DIR:-$HOME/Library/Application Support/Open Design/namespaces/release-stable/data}"
RUN_EVENTS="$OPEN_DESIGN_DATA_DIR/runs/$RUN_ID/events.jsonl"

STATUS=queued
ATTEMPTS=0
until [ "$STATUS" = "succeeded" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "canceled" ]; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ "$ATTEMPTS" -gt 1800 ]; then
    echo "Timeout waiting for OpenDesign generation run $RUN_ID." >&2
    exit 1
  fi
  sleep 2
  STATUS=$(curl -fsS --max-time 10 "$DAEMON/api/runs/$RUN_ID" | jq -r '.status')
  echo "run $RUN_ID status=$STATUS"
done

test "$STATUS" = "succeeded"
test -f "$RUN_EVENTS"

if rg -q "external_directory|auto-rejecting" "$RUN_EVENTS"; then
  echo "OpenDesign /api/runs reported success but OpenCode rejected workspace access." >&2
  echo "Re-run Phase 1 to refresh ~/.config/opencode/opencode.json external_directory allow rules." >&2
  echo "Restart the OpenDesign daemon outside any linked git repo, then start a fresh /api/runs generation." >&2
  exit 1
fi
````

Audit the generated workspace through the daemon endpoint. Fix every error and warning before copying. For missing or thin files, start another focused `/api/runs` generation on the same `PROJECT_ID`. Repeat the audit until `.audit.ok` is `true`.

```bash
AUDIT=$(curl -fsS --max-time 30 "$DAEMON/api/projects/$PROJECT_ID/design-system-package-audit")
echo "$AUDIT" | jq '.audit'
test "$(echo "$AUDIT" | jq -r '.audit.ok')" = "true"
```

Do not treat the draft as ready until the workspace directory has reviewable package artifacts and the daemon audit passes. Minimum checks:

```bash
test -f "$WORKSPACE_DIR/DESIGN.md"
test -f "$WORKSPACE_DIR/README.md"
test -f "$WORKSPACE_DIR/SKILL.md"
test -f "$WORKSPACE_DIR/colors_and_type.css"
test -f "$WORKSPACE_DIR/design-tokens.json"
test -f "$WORKSPACE_DIR/components.manifest.json"
test -d "$WORKSPACE_DIR/ui_kits/app"
test -f "$WORKSPACE_DIR/ui_kits/app/index.html"
test -f "$WORKSPACE_DIR/ui_kits/app/README.md"
test -f "$WORKSPACE_DIR/ui_kits/app/components/App.jsx"
test -d "$WORKSPACE_DIR/ui_kits/app/components"
test -d "$WORKSPACE_DIR/preview"
test -n "$(find "$WORKSPACE_DIR/preview" -name "*.html" -print -quit 2>/dev/null)"
```

When `revisionFeedback` is used after workspace generation, rerun `/api/runs` against the accepted draft and repeat these checks before publish/copy.

### Phase 4: Apply Revision When Requested

Skip this step when `revisionFeedback` is empty. Revision jobs create pending changes for the draft; accept the `revisionId` returned by the completed job. Do not query “latest pending”, because concurrent jobs can create unrelated pending revisions. If a revision is accepted after the workspace exists, run or continue workspace generation again before publish/copy so package artifacts reflect the accepted draft.

```bash
JOB=$(curl -fsS --max-time 30 -X POST "$DAEMON/api/design-systems/$DS/revision-jobs" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n \
    --arg feedback "$REVISION_FEEDBACK" \
    --arg sectionTitle "$SECTION_TITLE" \
    '{
      feedback: $feedback
    } + (if $sectionTitle == "" then {} else {sectionTitle: $sectionTitle} end)')" \
  | jq -r '.job.id')

STATUS=queued
ATTEMPTS=0
until [ "$STATUS" = "succeeded" ] || [ "$STATUS" = "failed" ]; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ "$ATTEMPTS" -gt 120 ]; then
    echo "Timeout waiting for revision job $JOB." >&2
    exit 1
  fi
  sleep 1
  STATUS=$(curl -fsS --max-time 10 "$DAEMON/api/design-systems/generation-jobs/$JOB" | jq -r .job.status)
done

JOB_JSON=$(curl -fsS --max-time 10 "$DAEMON/api/design-systems/generation-jobs/$JOB")
echo "$JOB_JSON" | jq '{status: .job.status, revisionId: .job.revisionId, error: .job.error}'

test "$STATUS" = "succeeded"

REV=$(echo "$JOB_JSON" | jq -r '.job.revisionId')

test -n "$REV"
test "$REV" != "null"

curl -fsS --max-time 30 -X PATCH "$DAEMON/api/design-systems/$DS/revisions/$REV" \
  -H 'Content-Type: application/json' \
  -d '{"status":"accepted"}' | jq .
```

### Phase 5: Publish

```bash
curl -fsS --max-time 30 -X PATCH "$DAEMON/api/design-systems/$DS" \
  -H 'Content-Type: application/json' \
  -d '{"status":"published"}' | jq -r '.designSystem.status'
```

Optional readback:

```bash
OPENDESIGN_CLI="${OPENDESIGN_CLI:-opendesign}"
"$OPENDESIGN_CLI" design-systems show "$DS" --json | jq '.body' -r
```

### Phase 6: Copy Generated Workspace Package

Copy from the generated workspace project, not from the seeded user design-system directory. The user design-system directory initially contains only the seeded draft files for agent-managed systems; the workspace project is where the OpenDesign agent writes the rich package artifacts.

```bash
OPEN_DESIGN_DATA_DIR="${OPEN_DESIGN_DATA_DIR:-$HOME/Library/Application Support/Open Design/namespaces/release-stable/data}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$OPEN_DESIGN_DATA_DIR/projects/$PROJECT_ID}"
PACKAGE_DIR="$WORKSPACE_DIR"

test -d "$PACKAGE_DIR"
test -f "$PACKAGE_DIR/DESIGN.md"
test -f "$PACKAGE_DIR/README.md"
test -f "$PACKAGE_DIR/SKILL.md"
test -d "$PACKAGE_DIR/ui_kits/app"

rm -rf rosey/design-system
mkdir -p rosey/design-system

# Copy package assets; skip OpenDesign workspace internals (.git, intake context, logs).
command -v rsync >/dev/null
rsync -a --exclude='.git' --exclude='context' --exclude='logs' "$PACKAGE_DIR/" rosey/design-system/

test -f rosey/design-system/DESIGN.md
test -f rosey/design-system/README.md
test -f rosey/design-system/SKILL.md
test -d rosey/design-system/ui_kits/app

mkdir -p rosey/designs
jq -n \
  --arg designSystemId "$DS" \
  --arg workspaceProjectId "$PROJECT_ID" \
  --arg sourceDir "$SOURCE_DIR" \
  --arg packageDir "$WORKSPACE_DIR" \
  --arg copiedPath "rosey/design-system" \
  --arg designPath "rosey/design-system/DESIGN.md" \
  --arg checksum "$(shasum -a 256 rosey/design-system/DESIGN.md | awk '{print $1}')" \
  --arg copiedAt "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    designSystemId: $designSystemId,
    workspaceProjectId: $workspaceProjectId,
    sourceDir: $sourceDir,
    packageDir: $packageDir,
    copiedPath: $copiedPath,
    designPath: $designPath,
    designChecksum: $checksum,
    copiedAt: $copiedAt
  }' > rosey/designs/design-system.json
```

## Handoff

After copying succeeds, report the seeded draft/workspace design system:

- Phase 0 `DESIGN.md` path and whether it was created or improved.
- OpenDesign design-system id.
- OpenDesign workspace project id.
- Whether revision feedback was applied.
- Copied package path: `rosey/design-system`.
- Async manifest path: `rosey/designs/design-system.json`.
- `HINDSIGHT: available|unavailable` — never omit

`rosey-design-catalog` can be invoked later; it auto-discovers `rosey/design-system/DESIGN.md`.

Emit this machine-readable block before finishing:

```text
ROSEY_DESIGN_SYSTEM_HANDOFF
SUCCESS: true|false
DESIGN_PATH: rosey/design-system/DESIGN.md
MANIFEST_PATH: rosey/designs/design-system.json
DESIGN_SYSTEM_ID: <id>
BLOCKERS: <none | reason>
HINDSIGHT: <available | unavailable> -- <brief reason>
END_ROSEY_DESIGN_SYSTEM_HANDOFF
```
