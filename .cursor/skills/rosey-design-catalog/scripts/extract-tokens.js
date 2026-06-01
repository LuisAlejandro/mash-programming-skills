#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { parseHtml } = require("../../rosey-implement-design/scripts/serialize-html.js");

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

function walk(node, visitor) {
  visitor(node);
  if (node.children) node.children.forEach((child) => walk(child, visitor));
}

function extractStyleBlocks(html) {
  const blocks = [];
  const regex = /<style\b[^>]*>([\s\S]*?)<\/style>/gi;
  let match;
  while ((match = regex.exec(html))) blocks.push(match[1]);
  return blocks;
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

  return cssParts;
}

function uniqueMatches(text, regex) {
  const values = new Set();
  let match;
  while ((match = regex.exec(text))) values.add(match[0]);
  return Array.from(values).sort();
}

function collectInlineStyles(root) {
  const declarations = [];
  walk(root, (node) => {
    if (node.type !== "element" || !node.attrs?.style) return;
    declarations.push(node.attrs.style);
  });
  return declarations;
}

function collectClasses(root) {
  const classes = new Set();
  walk(root, (node) => {
    if (node.type !== "element") return;
    (node.classes || []).forEach((className) => classes.add(className));
  });
  return Array.from(classes).sort();
}

function extractFontFamilies(text) {
  const families = new Set();
  const regex = /font-family\s*:\s*([^;}{]+)/gi;
  let match;
  while ((match = regex.exec(text))) families.add(match[1].trim());
  return Array.from(families).sort();
}

function extractDeclarations(text, propPattern) {
  const values = new Set();
  const regex = new RegExp(`(?:${propPattern})\\s*:\\s*([^;}{]+)`, "gi");
  let match;
  while ((match = regex.exec(text))) values.add(match[1].trim());
  return Array.from(values).sort();
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.html) {
    console.error("Usage: node extract-tokens.js --html <path> [--css <path[,path]>] [--assets-dir <dir>] [--out <path>]");
    process.exit(1);
  }

  const htmlPath = path.resolve(args.html);
  const html = fs.readFileSync(htmlPath, "utf8");
  const root = parseHtml(html);
  const styleText = [...extractStyleBlocks(html), ...readSupportCss(html, htmlPath, args), ...collectInlineStyles(root)].join("\n");
  const classes = collectClasses(root);
  const utilitySpacing = classes.filter((className) => /^(m|p|gap|space|inset|top|right|bottom|left|w|h|min|max)-/.test(className));
  const utilityTypography = classes.filter((className) => /^(text|font|leading|tracking)-/.test(className));
  const utilityColor = classes.filter((className) => /^(text|bg|border|fill|stroke)-/.test(className));

  const result = {
    source: { htmlPath },
    colors: uniqueMatches(styleText, /#(?:[0-9a-fA-F]{3,8})\b|rgba?\([^)]+\)|hsla?\([^)]+\)/g),
    gradients: uniqueMatches(styleText, /(?:linear|radial|conic)-gradient\([^)]+\)/g),
    shadows: extractDeclarations(styleText, "box-shadow|text-shadow|filter"),
    fontFamilies: extractFontFamilies(styleText),
    fontSizes: extractDeclarations(styleText, "font-size"),
    fontWeights: extractDeclarations(styleText, "font-weight"),
    lineHeights: extractDeclarations(styleText, "line-height"),
    spacing: uniqueMatches(styleText, /\b\d+(?:\.\d+)?(?:px|rem|em|vh|vw|%)\b/g),
    cssVariables: uniqueMatches(styleText, /--[A-Za-z0-9-_]+/g),
    classes,
    utilityClasses: {
      spacing: utilitySpacing,
      typography: utilityTypography,
      color: utilityColor,
    },
  };

  const json = JSON.stringify(result, null, 2);
  if (args.out) fs.writeFileSync(path.resolve(args.out), `${json}\n`);
  else process.stdout.write(`${json}\n`);
}

if (require.main === module) main();
