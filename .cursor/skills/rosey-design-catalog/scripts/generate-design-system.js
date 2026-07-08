#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");
const { buildCatalog } = require("../../rosey-implement-design/scripts/component-mapping.js");
const { loadDesignSystem } = require("../../rosey-implement-design/scripts/lib/parse-design-md");
const {
  loadDesignSystemManifest,
  readJsonIfExists,
  designsRoot,
  pageDir,
  latestPath,
  componentCatalogPath,
  rulesFilePath,
} = require("../../rosey-implement-design/scripts/lib/rosey-paths");

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

function fileChecksum(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
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
  for (const key of [
    "generatedAt",
    "htmlChecksum",
    "pageSlug",
    "artifact",
    "architecture",
    "tokens",
    "serialized",
    "componentCatalogPath",
    "rules",
  ]) {
    if (!(key in context)) throw new Error(`context.${key} is required`);
  }
  validateArtifact(context.artifact);
  assertObject(context.architecture, "context.architecture");
  assertObject(context.tokens, "context.tokens");
  assertObject(context.serialized, "context.serialized");
  if (!Array.isArray(context.serialized.controlInventory)) {
    throw new Error("context.serialized.controlInventory must be an array");
  }
  if (!context.rules.base) throw new Error("context.rules.base is required");
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

function renderBaseRules({ architecture, catalogPath, contextPath, pageSlug }) {
  return `${frontmatter({
    description: `Rosey OpenDesign-to-code conventions (${pageSlug})`,
    globs: ruleGlobs(architecture),
  })}# Rosey Design System

## Source Contract
- Source artifact is exported OpenDesign HTML/CSS, not vector data.
- Active page slug: \`${pageSlug}\` (re-run catalog when switching pages).
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

function main() {
  try {
    const args = parseArgs(process.argv.slice(2));
    const projectRoot = path.resolve(args["project-root"] || process.cwd());
    const htmlPath = assertHtmlFile(args.html);
    const scriptsDir = __dirname;
    const implementScripts = path.resolve(scriptsDir, "../../rosey-implement-design/scripts");
    const tokenScript = path.resolve(scriptsDir, "../../rosey-token-resolution/scripts/resolve-tokens.js");

    const architecture = runJson(path.join(scriptsDir, "scan-project-architecture.js"), ["--root", projectRoot]);
    const serialized = runJson(path.join(implementScripts, "serialize-html.js"), [
      "--html",
      htmlPath,
      ...(args["assets-dir"] ? ["--assets-dir", path.resolve(args["assets-dir"])] : []),
    ]);
    const designSystem = loadDesignSystem({
      designPath: args.design ? path.resolve(args.design) : null,
      htmlPath,
      projectRoot,
    });
    if (!designSystem && !args["allow-missing-design"]) {
      throw new Error(
        "DESIGN.md is required. Pass --design <path>, place it beside the HTML, or use rosey/design-system/DESIGN.md. Use --allow-missing-design only for HTML-only debugging.",
      );
    }

    const tokens = runJson(tokenScript, [
      "--html",
      htmlPath,
      "--project-root",
      projectRoot,
      ...(designSystem?.path ? ["--design", designSystem.path] : []),
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
    const pageDirPath = pageDir(projectRoot, pageSlug);
    const latestFile = latestPath(projectRoot);
    const catalogPath = componentCatalogPath(projectRoot);
    const contextPath = path.join(pageDirPath, "design-context.json");
    const artifactPath = path.join(pageDirPath, "artifact.json");
    const baseRulePath = rulesFilePath(projectRoot, "rosey-design-system");

    const pathAliases = Object.fromEntries(
      (architecture.pathAliases?.entries || []).map(([key, value]) => [key, path.resolve(projectRoot, value)]),
    );

    const dsManifest = loadDesignSystemManifest(projectRoot);
    if (dsManifest?.designPath && designSystem?.path) {
      const manifestPath = path.resolve(projectRoot, dsManifest.designPath);
      if (fs.existsSync(manifestPath) && dsManifest.designChecksum) {
        const currentDsChecksum = fileChecksum(manifestPath);
        if (currentDsChecksum !== dsManifest.designChecksum) {
          console.warn(
            "Warning: rosey/design-system/DESIGN.md changed since rosey-design-system copy. Re-run rosey-design-system or rosey-design-catalog.",
          );
        }
      }
    }

    const htmlChecksum = fileChecksum(htmlPath);
    const catalog = buildCatalog(projectRoot, {
      componentDirs: architecture.componentDirs,
      pathAliases,
    });
    const relContextPath = path.relative(projectRoot, contextPath);
    const context = {
      generatedAt: new Date().toISOString(),
      htmlChecksum,
      pageSlug,
      artifact: { ...artifact, htmlPath },
      architecture,
      tokens,
      designSystemResolved: tokens.designSystemResolved || null,
      resolvedTokens: tokens.resolvedTokens || null,
      failedTokens: tokens.failedTokens || [],
      serialized,
      componentCatalogPath: path.relative(projectRoot, catalogPath),
      ...(designSystem
        ? {
            designSystem: {
              ...designSystem,
              checksum: fileChecksum(designSystem.path),
              path: path.relative(projectRoot, designSystem.path),
            },
          }
        : {}),
      rules: {
        base: path.relative(projectRoot, baseRulePath),
      },
    };

    validateArtifact(artifact);
    validateCatalog(catalog);
    validateContext(context);

    writeJson(artifactPath, artifact);
    writeJson(catalogPath, catalog);
    writeJson(contextPath, context);
    const pageEntry = {
      generatedAt: context.generatedAt,
      pageSlug,
      htmlPath,
      htmlChecksum,
      artifactPath: path.relative(projectRoot, artifactPath),
      catalogPath: path.relative(projectRoot, catalogPath),
      contextPath: relContextPath,
      baseRulePath: path.relative(projectRoot, baseRulePath),
    };
    const existingLatest = readJsonIfExists(latestFile);
    const pages = existingLatest?.pages && typeof existingLatest.pages === "object" ? { ...existingLatest.pages } : {};
    pages[pageSlug] = pageEntry;
    writeJson(latestFile, {
      generatedAt: context.generatedAt,
      activePageSlug: pageSlug,
      pages,
    });
    writeText(baseRulePath, renderBaseRules({
      architecture,
      catalogPath: path.relative(projectRoot, catalogPath),
      contextPath: relContextPath,
      pageSlug,
    }));

    process.stdout.write(`${JSON.stringify({
      artifactPath: path.relative(projectRoot, artifactPath),
      catalogPath: path.relative(projectRoot, catalogPath),
      contextPath: path.relative(projectRoot, contextPath),
      latestPath: path.relative(projectRoot, latestFile),
      baseRulePath: path.relative(projectRoot, baseRulePath),
    }, null, 2)}\n`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

if (require.main === module) main();
