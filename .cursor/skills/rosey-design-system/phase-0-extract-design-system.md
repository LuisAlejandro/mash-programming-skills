# Phase 0: Extract Design System

## Objective

Analyze an existing frontend and create or refresh a `DESIGN.md` that documents the design system as implemented in the repo.

The workflow must work across React, Vue, Svelte, and static HTML projects. Detect the app structure first, then document only real tokens, styles, components, pages, and UX patterns found in the code.

## Inputs

Infer unless the user says otherwise:

- `sourceDir`: optional absolute path to the workspace root. Default: current git root.
- `appRoot`: optional app directory when the repo has a nested frontend. Default: infer from `package.json`, framework configs, and user-mentioned paths.
- `outputPath`: optional `DESIGN.md` path. Default: `<appRoot or sourceDir>/DESIGN.md`.
- `focus`: optional area to refresh, such as tokens, components, layout, navigation, forms, tables, data display, accessibility, or responsive behavior.

## Workflow

### Step 1: Validate Source

Confirm the source exists and identify the app root:

```bash
SOURCE_DIR="${SOURCE_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)}"
test -d "$SOURCE_DIR"
```

Use `Glob`, `rg`, and `ReadFile` to inspect:

- Product context: `README*`, docs, existing `DESIGN.md` if present.
- Framework signals: `package.json`, `vite.config.*`, `next.config.*`, `nuxt.config.*`, `svelte.config.*`, `astro.config.*`, `angular.json`, `vue.config.*`.
- Static HTML signals: `index.html`, `public/`, `assets/`, `css/`, `js/`, `src/`.
- Common app roots: `.`, `src/`, `app/`, `frontend/`, `client/`, `web/`, `ui/`, `packages/*`, or a user-mentioned path.

If multiple plausible app roots exist and the user did not specify one, pick the main UI only when obvious from scripts/docs. Otherwise ask which app to extract.

### Step 2: Analyze Design Sources

Read the files that define the actual system before writing prose.

Look for these source categories:

- Global styles and tokens: `*.css`, `*.scss`, `*.sass`, `*.less`, CSS variables, design-token files, theme files, Tailwind config, PostCSS config, CSS modules, styled-system files.
- Components: `components/`, `ui/`, `shared/`, `lib/`, `design-system/`, `primitives/`, and framework component files (`*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, custom elements).
- Pages and routes: `pages/`, `app/`, `routes/`, `views/`, router config, representative HTML pages.
- Layout and navigation: shells, headers, sidebars, breadcrumbs, tabs, menus, footers.
- Forms and data display: inputs, selects, validation, tables, cards, lists, charts, filters.
- Feedback and overlays: buttons, badges, alerts, toasts, dialogs, modals, drawers, popovers, loading, empty, and error states.
- Assets and branding: logos, icons, fonts, favicon, image conventions.
- Accessibility and responsiveness: focus styles, keyboard behavior, ARIA usage, breakpoints, motion preferences, reduced-motion styles.

Framework hints:

- React: inspect JSX/TSX components, hooks, component libraries, route files, CSS modules, styled components, or Tailwind/class utilities.
- Vue: inspect SFC `<template>`, `<script>`, `<style>`, composables, plugins, route views, and component libraries.
- Svelte: inspect `.svelte` markup, exported props, stores, actions, route files, and app-level styles.
- Static HTML: inspect repeated markup patterns, CSS classes, JS behavior, includes/partials/templates when present.

Extract only patterns implemented in the codebase. Prefer concrete paths, component names, props/events/slots, CSS variables, class utilities, states, and examples over generic design advice.

### Step 3: Write `DESIGN.md`

Create or update `DESIGN.md`. Use this structure and keep entries actionable:

```markdown
# Design System

## 0. Scope & Stack
- App/product: [name and purpose from README/package/docs]
- UI surface: [React/Vue/Svelte/static HTML/etc.]
- App root: [path]
- Styling: [CSS variables, Tailwind, Sass, CSS modules, component library, custom CSS, etc.]
- Component model: [framework components, web components, partials/templates, HTML patterns]
- Source paths: [canonical files and directories inspected]

## 1. Design Tokens
- Colors: semantic token groups, CSS variables, Tailwind names, intended usage
- Typography: font families, sizes, weights, line heights
- Spacing and sizing: spacing scale, widths, form control sizes
- Radius, shadows, transitions, z-index
- Dark mode or theme behavior when implemented

## 2. Core Components
- Primitive UI components: path, API, states, variants, when to use
- Layout/navigation: app shell, page layout, header/sidebar/footer, breadcrumb, tabs
- Forms: inputs, selects, validation, help text, disabled/error states
- Data display: tables, cards, lists, charts, pagination, filtering, row actions
- Overlays: modals, dialogs, drawers, popovers, dropdowns
- Feedback/status: toasts, loading, empty states, errors
- Domain components: product-specific reusable patterns

## 3. UX Patterns
- Page structure and responsive behavior
- Route/page conventions
- Data loading, errors, empty states, and destructive actions
- Accessibility rules already supported by code
- Internationalization, copy, and icon conventions when visible in UI code

## 4. Implementation Rules
- Reuse documented components and tokens before adding new styling
- Use existing import paths and variants
- Keep new UI consistent with the detected framework and local component patterns
- Note any clear anti-patterns, such as one-off colors or duplicated primitives

## 5. Gaps To Revisit
- Missing docs, unclear variants, duplicated styles, weak accessibility states, or components needing consolidation
```

Do not invent tokens or component APIs. If a section cannot be confirmed from the repo, write a short gap note instead of filling it with assumptions.

### Step 4: Verify

Before finishing:

- Re-read `DESIGN.md` and confirm every named token/component/path exists.
- Search for unrelated product names or workflow instructions from other repositories.
- Run available markdown or workspace checks when cheap. At minimum, use editor lints for `DESIGN.md`.

## Completion Report

Report:

- `DESIGN.md` path created or updated.
- Detected framework and app root.
- Main source paths inspected.
- High-confidence design areas documented.
- Gaps or low-confidence areas left for follow-up.

## Anti-Patterns

- Keep the output focused on `DESIGN.md`.
- Do not add enforcement rules unless the user explicitly asks.
- Do not document backend-only code as design-system source.
- Do not copy generic framework docs; document project patterns as implemented.
- Do not invent tokens, variants, or accessibility behavior not present in the repo.
