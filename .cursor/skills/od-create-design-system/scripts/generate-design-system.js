#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { buildCatalog } = require("../../od-implement-design/scripts/component-mapping.js");

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

function runJson(scriptPath, args) {
  const output = execFileSync(process.execPath, [scriptPath, ...args], { encoding: "utf8" });
  return JSON.parse(output);
}

function slugify(value) {
  return String(value || "opendesign-page")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "opendesign-page";
}

function assertHtmlFile(htmlPath) {
  if (!htmlPath) throw new Error("--html is required");
  const resolved = path.resolve(htmlPath);
  if (!fs.existsSync(resolved)) throw new Error(`HTML artifact not found: ${resolved}`);
  const stat = fs.statSync(resolved);
  if (!stat.isFile() || !/\.(html|htm)$/i.test(resolved)) {
    throw new Error(`OpenDesign artifact must be an existing .html/.htm file: ${resolved}`);
  }
  return resolved;
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function writeText(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, value);
}

function assertObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
}

function validateArtifact(artifact) {
  assertObject(artifact, "artifact");
  for (const key of ["name", "source", "htmlPath"]) {
    if (!artifact[key] || typeof artifact[key] !== "string") {
      throw new Error(`artifact.${key} must be a non-empty string`);
    }
  }
  if (artifact.source !== "opendesign-export") throw new Error("artifact.source must be opendesign-export");
}

function validateCatalog(catalog) {
  assertObject(catalog, "catalog");
  if (!catalog.generatedAt) throw new Error("catalog.generatedAt is required");
  if (!catalog.projectRoot) throw new Error("catalog.projectRoot is required");
  if (!Array.isArray(catalog.componentDirs)) throw new Error("catalog.componentDirs must be an array");
  assertObject(catalog.components, "catalog.components");
  for (const [name, component] of Object.entries(catalog.components)) {
    if (!name) throw new Error("catalog component name is required");
    if (!component.path || typeof component.path !== "string") throw new Error(`catalog.${name}.path is required`);
    if (!Array.isArray(component.matches)) throw new Error(`catalog.${name}.matches must be an array`);
    if (!Array.isArray(component.props)) throw new Error(`catalog.${name}.props must be an array`);
  }
}

function validateContext(context) {
  assertObject(context, "context");
  for (const key of ["generatedAt", "artifact", "architecture", "tokens", "serialized", "componentCatalogPath", "rules"]) {
    if (!(key in context)) throw new Error(`context.${key} is required`);
  }
  validateArtifact(context.artifact);
  assertObject(context.architecture, "context.architecture");
  assertObject(context.tokens, "context.tokens");
  assertObject(context.serialized, "context.serialized");
  if (!Array.isArray(context.serialized.controlInventory)) {
    throw new Error("context.serialized.controlInventory must be an array");
  }
  if (!context.rules.base || !context.rules.page) throw new Error("context.rules.base and context.rules.page are required");
}

function frontmatter({ description, globs }) {
  const globText = Array.isArray(globs)
    ? `globs:\n${globs.map((glob) => `  - ${JSON.stringify(glob)}`).join("\n")}`
    : `globs: ${JSON.stringify(globs)}`;
  return `---\ndescription: ${JSON.stringify(description)}\n${globText}\nalwaysApply: false\n---\n\n`;
}

function ruleGlobs(architecture) {
  const globs = [...(architecture.componentDirs || []), ...(architecture.routeDirs || [])].map((dir) => `${dir}/**`);
  return globs.length > 0 ? globs : "src/**";
}

function renderBaseRules({ architecture, catalogPath, contextPath }) {
  return `${frontmatter({
    description: "OpenDesign-to-code project conventions",
    globs: ruleGlobs(architecture),
  })}# OpenDesign Design System

## Source Contract
- Source artifact is exported OpenDesign HTML/CSS, not vector data.
- Required handoff context: \`${contextPath}\`.
- Component catalog: \`${catalogPath}\`.
- Use rendered baseline HTML for parity checks.

## Project Architecture
- Framework: \`${architecture.framework}\`
- Styling: \`${(architecture.styling || []).join(", ") || "unknown"}\`
- Component directories: \`${(architecture.componentDirs || []).join(", ") || "none detected"}\`
- Route directories: \`${(architecture.routeDirs || []).join(", ") || "none detected"}\`
- Asset directories: \`${(architecture.assetDirs || []).join(", ") || "none detected"}\`

## Implementation Rules
- Prefer existing components from the catalog before creating new primitives.
- Preserve semantic tags, ARIA attributes, labels, alt text, and keyboard behavior from the HTML.
- Map colors, spacing, typography, and shadows to project tokens when matches exist.
- Keep generated code idiomatic to the detected framework and local component patterns.
- Do not add OpenDesign MCP assumptions unless the MCP schema has been verified.
`;
}

function renderPageRules({ pageSlug, serialized, tokens }) {
  const controls = serialized.controlInventory || [];
  return `${frontmatter({
    description: `OpenDesign page overlay for ${pageSlug}`,
    globs: "src/**",
  })}# OpenDesign Page Overlay: ${pageSlug}

## Artifact
- HTML: \`${serialized.source.htmlPath}\`
- Assets: \`${serialized.source.assetsDir || "none"}\`
- Title: \`${serialized.title || pageSlug}\`

## Control Inventory
${controls.length === 0 ? "- No controls detected." : controls.map((item) => `- ${item.id}. [${item.kind}] ${item.text || item.attrs?.["aria-label"] || item.tag}`).join("\n")}

## Token Inventory
- Colors: ${(tokens.extractedTokens?.colors || []).join(", ") || "none detected"}
- Gradients: ${(tokens.extractedTokens?.gradients || []).join(", ") || "none detected"}
- Font families: ${(tokens.extractedTokens?.fontFamilies || []).join(", ") || "none detected"}

## Page Rules
- Treat every control inventory item as mandatory unless explicitly deferred.
- Compare implementation against rendered exported HTML at the same viewport.
- Use page-specific token matches from \`.cursor/od-design-context.json\` before raw values.
`;
}

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const projectRoot = path.resolve(args["project-root"] || process.cwd());
    const htmlPath = assertHtmlFile(args.html);
    const scriptsDir = __dirname;
    const implementScripts = path.resolve(scriptsDir, "../../od-implement-design/scripts");
    const tokenScript = path.resolve(scriptsDir, "../../od-token-resolution/scripts/resolve-tokens.js");

    const architecture = runJson(path.join(scriptsDir, "scan-project-architecture.js"), ["--root", projectRoot]);
    const serialized = runJson(path.join(implementScripts, "serialize-html.js"), [
      "--html",
      htmlPath,
      ...(args["assets-dir"] ? ["--assets-dir", path.resolve(args["assets-dir"])] : []),
    ]);
    const tokens = runJson(tokenScript, [
      "--html",
      htmlPath,
      "--project-root",
      projectRoot,
      ...(args.css ? ["--css", args.css] : []),
      ...(args["assets-dir"] ? ["--assets-dir", path.resolve(args["assets-dir"])] : []),
    ]);
    const artifact = runJson(path.join(implementScripts, "get-active-project.js"), [
      "--html",
      htmlPath,
      ...(args["preview-url"] ? ["--preview-url", args["preview-url"]] : []),
      ...(args["assets-dir"] ? ["--assets-dir", path.resolve(args["assets-dir"])] : []),
    ]);

    const pageSlug = slugify(args["page-slug"] || serialized.title || artifact.name);
    const cursorDir = path.join(projectRoot, ".cursor");
    const catalogPath = path.join(cursorDir, "od-component-catalog.json");
    const contextPath = path.join(cursorDir, "od-design-context.json");
    const artifactPath = path.join(cursorDir, "od-artifact.json");
    const baseRulePath = path.join(cursorDir, "rules", "od-design-system.mdc");
    const pageRulePath = path.join(cursorDir, "rules", `od-ds-${pageSlug}.mdc`);

    const catalog = buildCatalog(projectRoot, {
      componentDirs: architecture.componentDirs,
    });
    const context = {
      generatedAt: new Date().toISOString(),
      artifact,
      architecture,
      tokens,
      serialized,
      componentCatalogPath: path.relative(projectRoot, catalogPath),
      rules: {
        base: path.relative(projectRoot, baseRulePath),
        page: path.relative(projectRoot, pageRulePath),
      },
    };

    validateArtifact(artifact);
    validateCatalog(catalog);
    validateContext(context);

    writeJson(artifactPath, artifact);
    writeJson(catalogPath, catalog);
    writeJson(contextPath, context);
    writeText(baseRulePath, renderBaseRules({
      architecture,
      catalogPath: path.relative(projectRoot, catalogPath),
      contextPath: path.relative(projectRoot, contextPath),
    }));
    writeText(pageRulePath, renderPageRules({ pageSlug, serialized, tokens }));

    process.stdout.write(`${JSON.stringify({
      artifactPath: path.relative(projectRoot, artifactPath),
      catalogPath: path.relative(projectRoot, catalogPath),
      contextPath: path.relative(projectRoot, contextPath),
      baseRulePath: path.relative(projectRoot, baseRulePath),
      pageRulePath: path.relative(projectRoot, pageRulePath),
    }, null, 2)}\n`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
