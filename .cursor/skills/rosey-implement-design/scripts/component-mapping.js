#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { extractExports, extractProps } = require("./lib/ast-exports");
const { loadPathAliases, computeImportPath, resolveAliasImport } = require("./lib/project-paths");
const { loadDesignSystem } = require("./lib/parse-design-md");
const { loadLatestRosey, readJsonIfExists, assertHtmlFresh, pageDir, componentCatalogPath } = require("./lib/rosey-paths");
const { walkControls } = require("./serialize-html");

const { ROSEY_IGNORE_DIRS: IGNORE_DIRS } = require("./lib/scan-constants");

const COMPONENT_HINTS = {
  button: ["button"],
  link: ["link", "anchor", "nav"],
  input: ["input", "field", "text-field", "search"],
  select: ["select", "dropdown", "combobox"],
  textarea: ["textarea"],
  checkbox: ["checkbox"],
  radio: ["radio"],
  card: ["card", "panel", "tile"],
  dialog: ["dialog", "modal", "drawer"],
  heading: ["heading", "title", "typography", "text"],
  image: ["image", "avatar", "icon"],
  navbar: ["navbar", "nav", "header", "appbar", "topbar"],
  tabs: ["tabs", "tablist", "tab-panel"],
  accordion: ["accordion", "collapse", "disclosure"],
  carousel: ["carousel", "slider", "swiper"],
  grid: ["grid", "row", "col", "layout"],
  form: ["form"],
  list: ["list", "menu"],
  section: ["section", "hero", "banner", "footer"],
};

const DEFAULT_COMPONENT_DIRS = [
  "src/components",
  "app/components",
  "components",
  "src/ui",
  "lib/components",
  "packages/ui",
  "packages/design-system",
];

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) continue;
    const name = key.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) args[name] = true;
    else {
      args[name] = next;
      i += 1;
    }
  }
  return args;
}

function walkFiles(dir, files = []) {
  if (!fs.existsSync(dir)) return files;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (IGNORE_DIRS.has(entry.name)) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) walkFiles(fullPath, files);
    else if (
      /\.(tsx|jsx|ts|js|vue|svelte)$/.test(entry.name) &&
      !/\.(test|spec|stories|story)\.(tsx|jsx|ts|js|vue|svelte)$/.test(entry.name)
    ) {
      files.push(fullPath);
    }
  }
  return files;
}

function loadSerialized(args, projectRoot) {
  let context = null;
  let pageSlug = args["page-slug"] || null;

  if (args.context) {
    const contextPath = path.resolve(args.context);
    context = readJsonIfExists(contextPath);
  } else {
    try {
      const latest = loadLatestRosey(projectRoot, pageSlug);
      pageSlug = latest.pageSlug;
      context = readJsonIfExists(latest.contextPathAbs);
    } catch {
      context = null;
    }
  }

  if (context?.serialized) {
    const htmlPath = context.artifact?.htmlPath || context.serialized?.source?.htmlPath;
    if (htmlPath && !args["skip-stale-check"]) {
      assertHtmlFresh(context, htmlPath);
    }
    return { serialized: context.serialized, context, pageSlug: pageSlug || context.pageSlug };
  }

  if (args.serialized) {
    return { serialized: readJsonIfExists(path.resolve(args.serialized)), context: null, pageSlug };
  }

  return { serialized: null, context: null, pageSlug };
}

function retargetCatalogImports(catalog, projectRoot, targetFile) {
  if (!catalog?.components || !targetFile) return catalog;
  const aliases = loadPathAliases(projectRoot);
  const components = {};
  for (const [name, component] of Object.entries(catalog.components)) {
    components[name] = {
      ...component,
      suggestedImport: computeImportPath(targetFile, component.path, projectRoot, aliases),
    };
  }
  return { ...catalog, components };
}

function inferKinds(name, filePath, content) {
  const haystack = `${name} ${filePath} ${content.slice(0, 2000)}`.toLowerCase();
  const kinds = [];
  for (const [kind, hints] of Object.entries(COMPONENT_HINTS)) {
    if (hints.some((hint) => haystack.includes(hint))) kinds.push(kind);
  }
  return kinds;
}

function readArchitecture(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function resolveComponentDirs(projectRoot, options = {}) {
  if (options.componentDirs?.length) {
    return options.componentDirs.map((dir) => path.resolve(projectRoot, dir)).filter((dir) => fs.existsSync(dir));
  }

  const architecture = readArchitecture(options.architecturePath);
  if (architecture?.componentDirs?.length) {
    return architecture.componentDirs.map((dir) => path.resolve(projectRoot, dir)).filter((dir) => fs.existsSync(dir));
  }

  const defaults = DEFAULT_COMPONENT_DIRS.map((dir) => path.resolve(projectRoot, dir)).filter((dir) => fs.existsSync(dir));
  return defaults.length > 0 ? defaults : [projectRoot];
}

function buildCatalog(projectRoot, options = {}) {
  const componentDirs = resolveComponentDirs(projectRoot, options);
  const aliases = options.pathAliases || loadPathAliases(projectRoot);
  const files = componentDirs.flatMap((dir) => walkFiles(dir));
  const components = {};
  const defaultFromFile = options.defaultFromFile || "src/App.tsx";

  function shouldReplaceComponent(existingPath, nextPath) {
    const existingInPackages = existingPath.includes("packages/");
    const nextInPackages = nextPath.includes("packages/");
    if (existingInPackages && !nextInPackages) return true;
    if (!existingInPackages && nextInPackages) return false;
    return nextPath.length < existingPath.length;
  }

  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    const relPath = path.relative(projectRoot, file);
    for (const name of extractExports(content, file)) {
      const props = extractProps(content, file, name);
      const aliasImport = resolveAliasImport(relPath, projectRoot, aliases);
      const relativeImport = computeImportPath(defaultFromFile, relPath, projectRoot, aliases);
      const entry = {
        path: relPath,
        matches: inferKinds(name, file, content),
        props,
        suggestedImport: aliasImport || relativeImport,
      };
      if (components[name] && !shouldReplaceComponent(components[name].path, relPath)) continue;
      components[name] = entry;
    }
  }
  return {
    generatedAt: new Date().toISOString(),
    projectRoot,
    pathAliases: Object.keys(aliases),
    componentDirs: componentDirs.map((dir) => path.relative(projectRoot, dir) || "."),
    components,
  };
}

function classHaystack(node) {
  return `${(node.classes || []).join(" ")} ${node.attrs?.id || ""} ${node.attrs?.["aria-label"] || ""}`.toLowerCase();
}

function normalizeColor(value) {
  return String(value).trim().toLowerCase().replace(/\s+/g, "");
}

function buildDesignTokenHints(designSystem) {
  if (!designSystem?.tokens) return {};
  const hints = { colors: {}, typography: {}, spacing: {} };
  for (const [name, value] of Object.entries(designSystem.tokens.colors || {})) {
    hints.colors[normalizeColor(value)] = name;
  }
  return hints;
}

function inferTokenSuggestion(node, designTokenHints) {
  const styleColor = node.styles?.color || node.styles?.background || node.styles?.["background-color"];
  if (!styleColor) return null;
  const key = normalizeColor(styleColor);
  const tokenName = designTokenHints.colors[key];
  return tokenName ? { token: tokenName, value: styleColor } : null;
}

function scoreCandidate(kind, node, component, designTokenHints) {
  let score = 0;
  if (component.matches?.includes(kind)) score += 60;
  const name = component.name.toLowerCase();
  if (name.includes(kind)) score += 30;
  if (node.classes?.some((className) => name.includes(className.toLowerCase()))) score += 10;
  if (node.attrs?.disabled && component.props?.includes("disabled")) score += 5;
  if (node.attrs?.href && component.props?.some((prop) => ["href", "to"].includes(prop))) score += 5;
  if (inferTokenSuggestion(node, designTokenHints)) score += 3;
  return score;
}

function normalizeCatalog(catalog) {
  if (catalog.components) return catalog.components;
  return catalog;
}

function mapDom(serialized, catalog, options = {}) {
  const designTokenHints = buildDesignTokenHints(options.designSystem);
  const components = Object.entries(normalizeCatalog(catalog)).map(([name, value]) => ({ name, ...value }));
  const mappings = [];

  if (!serialized?.dom) return mappings;

  walkControls(serialized.dom, (node, kind, id, stableId) => {
    const ranked = components
      .map((component) => ({ component, score: scoreCandidate(kind, node, component, designTokenHints) }))
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score);

    const tokenHint = inferTokenSuggestion(node, designTokenHints);
    const candidate =
      ranked[0] && ranked[0].score >= 50
        ? {
            name: ranked[0].component.name,
            path: ranked[0].component.path,
            suggestedImport: ranked[0].component.suggestedImport,
            confidence: ranked[0].score,
            props: ranked[0].component.props || [],
          }
        : null;

    mappings.push({
      id,
      stableId,
      controlInventoryId: id,
      source: {
        tag: node.tag,
        kind,
        classes: node.classes || [],
        attrs: node.attrs || {},
      },
      designToken: tokenHint,
      candidate,
      fallback: candidate ? "catalog-match" : ranked[0] ? "low-confidence-review-required" : "create-or-inline",
    });
  });

  return mappings;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args["project-root"]) {
    console.error(
      "Usage: node component-mapping.js --project-root <root> [--page-slug <slug>] [--context <design-context.json>] [--serialized <serialized.json>] [--catalog <catalog.json>] [--target-file <path>] [--out <path>]",
    );
    process.exit(1);
  }

  const projectRoot = path.resolve(args["project-root"]);
  const { serialized, context, pageSlug } = loadSerialized(args, projectRoot);
  if (!serialized?.dom) {
    console.error("Serialized DOM missing. Run rosey-design-catalog first or pass --serialized.");
    process.exit(1);
  }

  let catalogPath = args.catalog ? path.resolve(args.catalog) : null;
  if (!catalogPath && context?.componentCatalogPath) {
    catalogPath = path.resolve(projectRoot, context.componentCatalogPath);
  }
  if (!catalogPath) {
    catalogPath = componentCatalogPath(projectRoot);
  }
  if (!catalogPath) {
    try {
      const latest = loadLatestRosey(projectRoot, pageSlug);
      catalogPath = latest.catalogPathAbs;
    } catch {
      catalogPath = null;
    }
  }

  const explicitCatalog = catalogPath ? readJsonIfExists(catalogPath) : null;
  const componentDirs = args["component-dirs"]
    ? args["component-dirs"].split(",").map((value) => value.trim()).filter(Boolean)
    : null;

  const designSystem =
    context?.designSystem ||
    loadDesignSystem({
      designPath: args.design ? path.resolve(args.design) : null,
      htmlPath: serialized.source?.htmlPath,
      projectRoot,
    });

  const catalog =
    explicitCatalog ||
    buildCatalog(projectRoot, {
      componentDirs,
      architecturePath: args.architecture ? path.resolve(args.architecture) : null,
      defaultFromFile: args["target-file"] || "src/App.tsx",
      pathAliases: context?.architecture?.pathAliases
        ? Object.fromEntries(
            (context.architecture.pathAliases.entries || []).map(([k, v]) => [k, path.resolve(projectRoot, v)]),
          )
        : loadPathAliases(projectRoot),
    });
  const targetFile = args["target-file"] || null;
  const mappedCatalog = retargetCatalogImports(catalog, projectRoot, targetFile);

  const result = {
    generatedAt: new Date().toISOString(),
    projectRoot,
    pageSlug: pageSlug || context?.pageSlug || null,
    source: context
      ? path.join("docs", "designs", context.pageSlug || pageSlug || "<page-slug>", "design-context.json")
      : args.serialized || "inline",
    designSystem: designSystem ? { title: designSystem.title, path: designSystem.path } : null,
    designSystemResolved: context?.designSystemResolved || context?.tokens?.designSystemResolved || null,
    resolvedTokens: context?.resolvedTokens || context?.tokens?.resolvedTokens || null,
    catalog: mappedCatalog,
    mappings: mapDom(serialized, mappedCatalog, { designSystem }),
  };

  const defaultOut =
    pageSlug || context?.pageSlug
      ? path.join(pageDir(projectRoot, pageSlug || context.pageSlug), "component-mapping.json")
      : null;
  const outPath = args.out ? path.resolve(args.out) : defaultOut;
  const json = JSON.stringify(result, null, 2);
  if (outPath) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, `${json}\n`);
  } else {
    process.stdout.write(`${json}\n`);
  }
}

if (require.main === module) main();

module.exports = { buildCatalog, mapDom, loadSerialized };
