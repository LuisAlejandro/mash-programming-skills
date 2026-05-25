#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { parse: parseDocument } = require("node-html-parser");

const VOID_TAGS = new Set([
  "area",
  "base",
  "br",
  "col",
  "embed",
  "hr",
  "img",
  "input",
  "link",
  "meta",
  "param",
  "source",
  "track",
  "wbr",
]);

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) continue;
    const name = key.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[name] = true;
    } else {
      args[name] = next;
      i += 1;
    }
  }
  return args;
}

function parseAttributes(raw) {
  const attrs = {};
  const attrRegex = /([:@A-Za-z_][:@A-Za-z0-9_.-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  let match;
  while ((match = attrRegex.exec(raw))) {
    const [, key, doubleValue, singleValue, bareValue] = match;
    attrs[key] = doubleValue ?? singleValue ?? bareValue ?? true;
  }
  return attrs;
}

function parseStyle(styleValue) {
  if (!styleValue || typeof styleValue !== "string") return {};
  return styleValue.split(";").reduce((styles, declaration) => {
    const index = declaration.indexOf(":");
    if (index === -1) return styles;
    const key = declaration.slice(0, index).trim();
    const value = declaration.slice(index + 1).trim();
    if (key && value) styles[key] = value;
    return styles;
  }, {});
}

function textContent(node) {
  if (node.type === "text") return node.value;
  if (!node.children) return "";
  return node.children.map(textContent).join(" ").replace(/\s+/g, " ").trim();
}

function normalizeParsedNode(parsedNode) {
  const tag = (parsedNode.rawTagName || parsedNode.tagName || "").toLowerCase();
  if (!tag) {
    const children = parsedNode.childNodes || [];
    if (children.length > 0) {
      return {
        type: "root",
        children: children.map(normalizeParsedNode).filter(Boolean),
      };
    }

    const value = (parsedNode.text || parsedNode.rawText || "").replace(/\s+/g, " ").trim();
    return value ? { type: "text", value } : null;
  }

  if (tag === "script" || tag === "style") {
    return {
      type: "element",
      tag,
      attrs: parsedNode.attributes || {},
      classes: [],
      styles: {},
      children: [],
    };
  }

  const attrs = parsedNode.attributes || {};
  return {
    type: "element",
    tag,
    attrs,
    classes: typeof attrs.class === "string" ? attrs.class.split(/\s+/).filter(Boolean) : [],
    styles: parseStyle(attrs.style),
    children: (parsedNode.childNodes || []).map(normalizeParsedNode).filter(Boolean),
  };
}

function parseHtmlWithLibrary(html) {
  const parsed = parseDocument(html, {
    blockTextElements: {
      script: true,
      noscript: true,
      style: true,
      pre: true,
    },
    comment: false,
  });
  const normalized = normalizeParsedNode(parsed);
  return normalized?.type === "root" ? normalized : { type: "root", children: normalized ? [normalized] : [] };
}

function parseHtmlFallback(html) {
  const parseableHtml = html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, "<style></style>");
  const root = { type: "root", children: [] };
  const stack = [root];
  const tokenRegex = /<!--[\s\S]*?-->|<![^>]*>|<\/?[A-Za-z][^>]*>|[^<]+/g;
  let match;

  while ((match = tokenRegex.exec(parseableHtml))) {
    const token = match[0];
    const parent = stack[stack.length - 1];

    if (token.startsWith("<!--") || token.startsWith("<!")) continue;

    if (!token.startsWith("<")) {
      const value = token.replace(/\s+/g, " ").trim();
      if (value) parent.children.push({ type: "text", value });
      continue;
    }

    if (token.startsWith("</")) {
      const closeTag = token.slice(2, -1).trim().toLowerCase();
      while (stack.length > 1) {
        const current = stack.pop();
        if (current.tag === closeTag) break;
      }
      continue;
    }

    const selfClosing = token.endsWith("/>");
    const tagMatch = token.match(/^<\s*([A-Za-z][A-Za-z0-9:-]*)\s*([\s\S]*?)\/?>$/);
    if (!tagMatch) continue;

    const tag = tagMatch[1].toLowerCase();
    const attrs = parseAttributes(tagMatch[2] || "");
    const node = {
      type: "element",
      tag,
      attrs,
      classes: typeof attrs.class === "string" ? attrs.class.split(/\s+/).filter(Boolean) : [],
      styles: parseStyle(attrs.style),
      children: [],
    };

    parent.children.push(node);
    if (!selfClosing && !VOID_TAGS.has(tag)) stack.push(node);
  }

  return root;
}

function parseHtml(html) {
  return parseHtmlWithLibrary(html);
}

function extractStyleBlocks(html) {
  const blocks = [];
  const regex = /<style\b[^>]*>([\s\S]*?)<\/style>/gi;
  let match;
  while ((match = regex.exec(html))) blocks.push(match[1].trim());
  return blocks;
}

function extractCssVariables(styleBlocks) {
  const variables = {};
  for (const block of styleBlocks) {
    const regex = /(--[A-Za-z0-9-_]+)\s*:\s*([^;}{]+)/g;
    let match;
    while ((match = regex.exec(block))) {
      variables[match[1]] = match[2].trim();
    }
  }
  return variables;
}

function walk(node, visitor) {
  visitor(node);
  if (node.children) node.children.forEach((child) => walk(child, visitor));
}

function isHidden(node) {
  if (node.type !== "element") return false;
  if (node.attrs.hidden === true || node.attrs["aria-hidden"] === "true") return true;
  const display = node.styles.display;
  const visibility = node.styles.visibility;
  return display === "none" || visibility === "hidden";
}

function classifyControl(node) {
  if (node.type !== "element" || isHidden(node)) return null;
  const role = node.attrs.role;
  const type = node.attrs.type;

  if (node.tag === "button" || role === "button") return "button";
  if (node.tag === "a" && node.attrs.href) return "link";
  if (node.tag === "input") return type || "input";
  if (node.tag === "select") return "select";
  if (node.tag === "textarea") return "textarea";
  if (["checkbox", "radio", "switch", "tab", "menuitem", "dialog"].includes(role)) return role;
  if (/^h[1-6]$/.test(node.tag)) return "heading";
  if (node.tag === "img" || node.tag === "svg") return "image";
  return null;
}

function collectInventory(root) {
  const inventory = [];
  let index = 1;
  walk(root, (node) => {
    const kind = classifyControl(node);
    if (!kind) return;
    inventory.push({
      id: index,
      kind,
      tag: node.tag,
      text: textContent(node).slice(0, 120),
      classes: node.classes,
      attrs: Object.fromEntries(
        Object.entries(node.attrs).filter(([key]) =>
          ["id", "name", "type", "role", "aria-label", "href", "alt", "placeholder"].includes(key),
        ),
      ),
    });
    index += 1;
  });
  return inventory;
}

function collectClasses(root) {
  const classes = new Set();
  walk(root, (node) => {
    if (node.type === "element") node.classes.forEach((className) => classes.add(className));
  });
  return Array.from(classes).sort();
}

function collectAssets(root, styleBlocks, htmlPath, assetsDir) {
  const refs = new Set();
  walk(root, (node) => {
    if (node.type !== "element") return;
    ["src", "href", "poster"].forEach((attr) => {
      if (typeof node.attrs[attr] === "string") refs.add(node.attrs[attr]);
    });
    Object.values(node.styles).forEach((value) => {
      const regex = /url\((['"]?)(.*?)\1\)/g;
      let match;
      while ((match = regex.exec(value))) refs.add(match[2]);
    });
  });
  for (const block of styleBlocks) {
    const regex = /url\((['"]?)(.*?)\1\)/g;
    let match;
    while ((match = regex.exec(block))) refs.add(match[2]);
  }

  return Array.from(refs).map((ref) => ({
    ref,
    resolvedPath:
      ref.startsWith("http") || ref.startsWith("data:")
        ? null
        : path.resolve(assetsDir || path.dirname(htmlPath), ref),
  }));
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.html) {
    console.error("Usage: node serialize-html.js --html <path> [--assets-dir <path>] [--out <path>]");
    process.exit(1);
  }

  const htmlPath = path.resolve(args.html);
  const html = fs.readFileSync(htmlPath, "utf8");
  const root = parseHtml(html);
  const styleBlocks = extractStyleBlocks(html);
  const result = {
    source: {
      htmlPath,
      assetsDir: args["assets-dir"] ? path.resolve(args["assets-dir"]) : null,
    },
    parser: {
      name: "node-html-parser",
      fallback: "parseHtmlFallback is retained only for emergency debugging.",
    },
    title: (html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i) || [null, null])[1],
    dom: root,
    styleBlocks,
    cssVariables: extractCssVariables(styleBlocks),
    classes: collectClasses(root),
    assets: collectAssets(root, styleBlocks, htmlPath, args["assets-dir"]),
    controlInventory: collectInventory(root),
  };

  const json = JSON.stringify(result, null, 2);
  if (args.out) fs.writeFileSync(path.resolve(args.out), `${json}\n`);
  else process.stdout.write(`${json}\n`);
}

if (require.main === module) main();

module.exports = {
  parseHtml,
  parseHtmlFallback,
  parseAttributes,
  parseStyle,
  textContent,
  collectInventory,
  collectClasses,
};
