#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { loadDesignSystem } = require("../../rosey-implement-design/scripts/lib/parse-design-md");

const { ROSEY_IGNORE_DIRS: IGNORE_DIRS } = require("../../rosey-implement-design/scripts/lib/scan-constants");

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

function walkFiles(dir, predicate, results = []) {
  if (!dir || !fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (IGNORE_DIRS.has(entry.name)) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) walkFiles(fullPath, predicate, results);
    else if (predicate(fullPath)) results.push(fullPath);
  }
  return results;
}

function uniqueMatches(text, regex) {
  const values = new Set();
  let match;
  while ((match = regex.exec(text))) values.add(match[0]);
  return Array.from(values).sort();
}

function extractCssVariables(text) {
  const variables = {};
  const regex = /(--[A-Za-z0-9-_]+)\s*:\s*([^;}{]+)/g;
  let match;
  while ((match = regex.exec(text))) variables[match[1]] = match[2].trim();
  return variables;
}

function readSupportCss(html, htmlPath, args) {
  const cssParts = [];
  if (args.css) {
    for (const cssPath of args.css.split(",").map((value) => value.trim()).filter(Boolean)) {
      const resolved = path.resolve(cssPath);
      if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) cssParts.push(fs.readFileSync(resolved, "utf8"));
    }
  }

  const baseDir = args["assets-dir"] ? path.resolve(args["assets-dir"]) : path.dirname(htmlPath);
  const linkRegex = /<link\b[^>]*rel=["']?stylesheet["']?[^>]*href=["']([^"']+)["'][^>]*>/gi;
  let match;
  while ((match = linkRegex.exec(html))) {
    const href = match[1];
    if (/^(https?:|data:)/i.test(href)) continue;
    const resolved = path.resolve(baseDir, href);
    if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) cssParts.push(fs.readFileSync(resolved, "utf8"));
  }

  return cssParts.join("\n");
}

function extractArtifactTokens(htmlPath, args = {}) {
  const html = fs.readFileSync(htmlPath, "utf8");
  const css = readSupportCss(html, htmlPath, args);
  const text = `${html}\n${css}`;
  return {
    cssVariables: extractCssVariables(text),
    colors: uniqueMatches(text, /#(?:[0-9a-fA-F]{3,8})\b|rgba?\([^)]+\)|hsla?\([^)]+\)/g),
    gradients: uniqueMatches(text, /(?:linear|radial|conic)-gradient\([^)]+\)/g),
    spacing: uniqueMatches(text, /\b\d+(?:\.\d+)?(?:px|rem|em|vh|vw|%)\b/g),
    fontFamilies: uniqueMatches(text, /font-family\s*:\s*[^;}{]+/gi).map((value) => value.split(":").slice(1).join(":").trim()),
    classNames: uniqueMatches(text, /class=["']([^"']+)["']/g)
      .flatMap((classAttr) => classAttr.replace(/^class=["']|["']$/g, "").split(/\s+/))
      .filter(Boolean)
      .sort(),
  };
}

function extractProjectTokens(projectRoot) {
  const files = walkFiles(projectRoot, (filePath) => /\.(css|scss|sass|ts|js|json)$/.test(filePath));
  const tokens = {};
  const values = {};

  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    const variables = extractCssVariables(content);
    for (const [name, value] of Object.entries(variables)) {
      tokens[name] = { value, file: path.relative(projectRoot, file) };
      const key = normalize(value);
      if (!values[key]) values[key] = [];
      values[key].push(name);
    }
  }

  return { tokens, values };
}

function normalize(value) {
  return String(value).trim().toLowerCase().replace(/\s+/g, " ");
}

function resolveValues(values, projectTokens) {
  const resolved = {};
  const failed = [];
  for (const value of values) {
    const key = normalize(value);
    const matches = projectTokens.values[key] || [];
    if (matches.length > 0) resolved[value] = matches;
    else failed.push(value);
  }
  return { resolved, failed };
}

function resolveDesignSystemTokens(designSystem, projectTokens) {
  if (!designSystem?.tokens) return { colors: {}, typography: {}, spacing: {} };
  const resolved = { colors: {}, typography: {}, spacing: {} };

  for (const [name, value] of Object.entries(designSystem.tokens.colors || {})) {
    const key = normalize(value);
    const matches = projectTokens.values[key] || [];
    resolved.colors[name] = {
      designValue: value,
      projectTokens: matches,
      status: matches.length > 0 ? "mapped" : "unmapped",
    };
  }

  for (const [name, value] of Object.entries(designSystem.tokens.typography || {})) {
    resolved.typography[name] = { designValue: value, status: "reference" };
  }

  for (const [name, value] of Object.entries(designSystem.tokens.spacing || {})) {
    resolved.spacing[name] = { designValue: value, status: "reference" };
  }

  return resolved;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.html) {
    console.error(
      "Usage: node resolve-tokens.js --html <path> [--project-root <root>] [--design <DESIGN.md>] [--css <path[,path]>] [--assets-dir <dir>] [--out <path>]",
    );
    process.exit(1);
  }

  const htmlPath = path.resolve(args.html);
  const extractedTokens = extractArtifactTokens(htmlPath, args);
  const projectRoot = args["project-root"] ? path.resolve(args["project-root"]) : null;
  const projectTokens = projectRoot ? extractProjectTokens(projectRoot) : { tokens: {}, values: {} };

  const designSystem = loadDesignSystem({
    designPath: args.design ? path.resolve(args.design) : null,
    htmlPath,
    projectRoot,
  });
  if (!designSystem && args["require-design"]) {
    console.error("DESIGN.md is required. Pass --design <path> or place it at docs/design-system/DESIGN.md.");
    process.exit(1);
  }

  const tokenValues = [
    ...Object.values(extractedTokens.cssVariables),
    ...extractedTokens.colors,
    ...extractedTokens.gradients,
    ...extractedTokens.spacing,
    ...Object.values(designSystem?.tokens?.colors || {}),
  ];
  const { resolved, failed } = resolveValues(Array.from(new Set(tokenValues)), projectTokens);
  const designSystemResolved = designSystem ? resolveDesignSystemTokens(designSystem, projectTokens) : null;

  const result = {
    source: { htmlPath, projectRoot, designPath: designSystem?.path || null },
    extractedTokens,
    designSystem: designSystem
      ? { title: designSystem.title, category: designSystem.category, tokens: designSystem.tokens }
      : null,
    designSystemResolved,
    projectTokens: projectTokens.tokens,
    resolvedTokens: resolved,
    failedTokens: failed,
  };

  const json = JSON.stringify(result, null, 2);
  if (args.out) fs.writeFileSync(path.resolve(args.out), `${json}\n`);
  else process.stdout.write(`${json}\n`);
}

if (require.main === module) main();
