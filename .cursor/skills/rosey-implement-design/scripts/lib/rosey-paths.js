const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

/** Project-relative root for OpenDesign pipeline artifacts (not rules or DESIGN.md). */
const DESIGNS_DIR = path.join("rosey", "designs");

/**
 * Detect which Rosey tree this script is running from, based on its own location.
 * - .cursor/skills/**  -> Cursor tree  -> rules live in .cursor/rules/*.mdc
 * - .github/skills/**  -> VS Code tree -> rules live in .github/instructions/*.instructions.md
 * Fallback: prefer .cursor/rules if it exists, else .github/instructions.
 */
function treeKind() {
  const segments = __dirname.split(path.sep);
  if (segments.includes(".cursor")) return "cursor";
  if (segments.includes(".github")) return "vscode";
  return null;
}

function rulesRoot(projectRoot) {
  const kind = treeKind();
  if (kind === "cursor") return path.join(projectRoot, ".cursor", "rules");
  if (kind === "vscode") return path.join(projectRoot, ".github", "instructions");
  const cursorRules = path.join(projectRoot, ".cursor", "rules");
  return fs.existsSync(cursorRules) ? cursorRules : path.join(projectRoot, ".github", "instructions");
}

function rulesFileExtension() {
  const kind = treeKind();
  if (kind === "vscode") return ".instructions.md";
  return ".mdc";
}

/** Absolute path to a Rosey rule file, target-aware. ruleName excludes extension. */
function rulesFilePath(projectRoot, ruleName) {
  return path.join(rulesRoot(projectRoot), `${ruleName}${rulesFileExtension()}`);
}

function designsRoot(projectRoot) {
  return path.join(projectRoot, DESIGNS_DIR);
}

function latestPath(projectRoot) {
  return path.join(designsRoot(projectRoot), "latest.json");
}

function componentCatalogPath(projectRoot) {
  return path.join(designsRoot(projectRoot), "component-catalog.json");
}

function designSystemManifestPath(projectRoot) {
  return path.join(designsRoot(projectRoot), "design-system.json");
}

function pageDir(projectRoot, pageSlug) {
  return path.join(designsRoot(projectRoot), pageSlug);
}

function pageReviewDir(projectRoot, pageSlug) {
  return path.join(pageDir(projectRoot, pageSlug), "review");
}

function sourceDir(projectRoot, pageSlug) {
  return path.join(pageDir(projectRoot, pageSlug), "source");
}

function readJsonIfExists(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function fileChecksum(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function resolveProjectPath(projectRoot, relativeOrAbsolute) {
  if (!relativeOrAbsolute) return null;
  return path.isAbsolute(relativeOrAbsolute)
    ? relativeOrAbsolute
    : path.resolve(projectRoot, relativeOrAbsolute);
}

function normalizeLatestEntry(projectRoot, pageSlug, entry) {
  return {
    pageSlug,
    htmlPath: entry.htmlPath,
    htmlChecksum: entry.htmlChecksum,
    artifactPath: entry.artifactPath,
    catalogPath: entry.catalogPath,
    contextPath: entry.contextPath,
    baseRulePath: entry.baseRulePath,
    generatedAt: entry.generatedAt,
    contextPathAbs: resolveProjectPath(projectRoot, entry.contextPath),
    catalogPathAbs: resolveProjectPath(projectRoot, entry.catalogPath),
    artifactPathAbs: resolveProjectPath(projectRoot, entry.artifactPath),
    reviewDir: pageReviewDir(projectRoot, pageSlug),
  };
}

function migrateLegacyLatest(projectRoot, latest) {
  const pageSlug = latest.pageSlug || "opendesign-page";
  const entry = {
    pageSlug,
    htmlPath: latest.htmlPath || null,
    htmlChecksum: latest.htmlChecksum || null,
    artifactPath: latest.artifactPath,
    catalogPath: latest.catalogPath,
    contextPath: latest.contextPath,
    baseRulePath: latest.baseRulePath,
    generatedAt: latest.generatedAt,
  };
  return {
    generatedAt: latest.generatedAt,
    activePageSlug: pageSlug,
    pages: { [pageSlug]: entry },
  };
}

function loadLatestRosey(projectRoot, pageSlug) {
  const latestFile = latestPath(projectRoot);
  let latest = readJsonIfExists(latestFile);
  if (!latest) return null;

  if (!latest.pages && latest.contextPath) {
    latest = migrateLegacyLatest(projectRoot, latest);
  }

  const slug = pageSlug || latest.activePageSlug;
  if (!slug) {
    throw new Error("No active page in rosey/designs/latest.json. Pass --page-slug or run rosey-design-catalog.");
  }

  const entry = latest.pages?.[slug];
  if (!entry) {
    throw new Error(`Page slug not found in latest.json: ${slug}. Known: ${Object.keys(latest.pages || {}).join(", ") || "none"}`);
  }

  const normalized = normalizeLatestEntry(projectRoot, slug, entry);
  return { latestPath: latestFile, latest, ...normalized };
}

function loadDesignSystemManifest(projectRoot) {
  return readJsonIfExists(designSystemManifestPath(projectRoot));
}

function assertHtmlFresh(context, htmlPath) {
  if (!context?.htmlChecksum || !htmlPath) return;
  if (!fs.existsSync(htmlPath)) {
    throw new Error(`HTML artifact missing: ${htmlPath}. Re-run rosey-design-catalog.`);
  }
  const current = fileChecksum(htmlPath);
  if (current !== context.htmlChecksum) {
    throw new Error(
      "HTML artifact changed since design-context was generated. Re-run rosey-design-catalog before implement.",
    );
  }
}

module.exports = {
  DESIGNS_DIR,
  designsRoot,
  latestPath,
  componentCatalogPath,
  designSystemManifestPath,
  pageDir,
  pageReviewDir,
  sourceDir,
  readJsonIfExists,
  fileChecksum,
  loadLatestRosey,
  loadDesignSystemManifest,
  assertHtmlFresh,
  resolveProjectPath,
  treeKind,
  rulesRoot,
  rulesFileExtension,
  rulesFilePath,
};
