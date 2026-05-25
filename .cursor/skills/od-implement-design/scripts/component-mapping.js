#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const IGNORE_DIRS = new Set([
  ".git",
  ".next",
  ".turbo",
  "coverage",
  "dist",
  "build",
  "node_modules",
]);

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

function readJsonIfExists(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function extractExports(content, filePath) {
  const names = new Set();
  const patterns = [
    /export\s+(?:default\s+)?function\s+([A-Z][A-Za-z0-9_]*)/g,
    /export\s+(?:const|let|var)\s+([A-Z][A-Za-z0-9_]*)/g,
    /function\s+([A-Z][A-Za-z0-9_]*)\s*\(/g,
    /const\s+([A-Z][A-Za-z0-9_]*)\s*=/g,
  ];
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(content))) names.add(match[1]);
  }
  if (names.size === 0) {
    const base = path.basename(filePath).replace(/\.(tsx|jsx|ts|js|vue|svelte)$/, "");
    if (/^[A-Z]/.test(base)) names.add(base);
  }
  return Array.from(names);
}

function extractProps(content, componentName) {
  const props = new Set();
  const escapedName = componentName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const specificInterface = content.match(new RegExp(`interface\\s+${escapedName}Props(?:\\s+extends\\s+([^{]+))?\\s*{([\\s\\S]*?)}`));
  const specificType = content.match(new RegExp(`type\\s+${escapedName}Props\\s*=\\s*([\\s\\S]*?)(?:;|\\n\\n)`));
  const interfaceMatch = specificInterface || content.match(/interface\s+[A-Za-z0-9_]*Props\s*{([\s\S]*?)}/);
  const typeMatch = specificType || content.match(/type\s+[A-Za-z0-9_]*Props\s*=\s*{([\s\S]*?)}/);
  const body = interfaceMatch?.[2] || interfaceMatch?.[1] || typeMatch?.[1] || "";
  const propRegex = /([A-Za-z_$][A-Za-z0-9_$]*)\??\s*:/g;
  let match;
  while ((match = propRegex.exec(body))) props.add(match[1]);

  const destructuredPatterns = [
    new RegExp(`function\\s+${escapedName}\\s*\\(\\s*{([\\s\\S]*?)}\\s*[:)=,]`),
    new RegExp(`(?:const|let|var)\\s+${escapedName}\\s*=\\s*(?:forwardRef\\s*\\([^=]*=>\\s*)?\\(?\\s*{([\\s\\S]*?)}\\s*[:)=,]`),
  ];
  for (const pattern of destructuredPatterns) {
    const destructured = content.match(pattern)?.[1] || "";
    for (const part of destructured.split(",")) {
      const name = part.trim().match(/^([A-Za-z_$][A-Za-z0-9_$]*)/)?.[1];
      if (name && !["className", "children", "props", "ref"].includes(name)) props.add(name);
    }
  }

  const componentPropsRegex = /ComponentProps(?:WithoutRef|WithRef)?\s*<\s*["']([A-Za-z0-9-]+)["']\s*>/g;
  while ((match = componentPropsRegex.exec(body))) {
    props.add(`html:${match[1]}`);
  }

  const variantsMatch = content.match(/variants\s*:\s*{([\s\S]*?)},?\s*(?:defaultVariants|compoundVariants|\)\s*$)/);
  const variantsBody = variantsMatch?.[1] || "";
  const variantKeyRegex = /([A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*{/g;
  while ((match = variantKeyRegex.exec(variantsBody))) props.add(match[1]);

  return Array.from(props);
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
  const files = componentDirs.flatMap((dir) => walkFiles(dir));
  const components = {};
  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    for (const name of extractExports(content, file)) {
      const props = extractProps(content, name);
      components[name] = {
        path: path.relative(projectRoot, file),
        matches: inferKinds(name, file, content),
        props,
      };
    }
  }
  return {
    generatedAt: new Date().toISOString(),
    projectRoot,
    componentDirs: componentDirs.map((dir) => path.relative(projectRoot, dir) || "."),
    components,
  };
}

function walkDom(node, visitor) {
  visitor(node);
  if (node.children) node.children.forEach((child) => walkDom(child, visitor));
}

function elementKind(node) {
  if (node.type !== "element") return null;
  const role = node.attrs?.role;
  const type = node.attrs?.type;
  if (node.tag === "button" || role === "button") return "button";
  if (node.tag === "a" && node.attrs?.href) return "link";
  if (node.tag === "input") return type || "input";
  if (node.tag === "select") return "select";
  if (node.tag === "textarea") return "textarea";
  if (role) return role;
  if (/^h[1-6]$/.test(node.tag)) return "heading";
  if (node.tag === "img" || node.tag === "svg") return "image";
  if (node.classes?.some((className) => /card|panel|tile/.test(className))) return "card";
  return null;
}

function scoreCandidate(kind, node, component) {
  let score = 0;
  if (component.matches?.includes(kind)) score += 60;
  const name = component.name.toLowerCase();
  if (name.includes(kind)) score += 30;
  if (node.classes?.some((className) => name.includes(className.toLowerCase()))) score += 10;
  if (node.attrs?.disabled && component.props?.includes("disabled")) score += 5;
  if (node.attrs?.href && component.props?.some((prop) => ["href", "to"].includes(prop))) score += 5;
  return score;
}

function normalizeCatalog(catalog) {
  if (catalog.components) return catalog.components;
  return catalog;
}

function mapDom(serialized, catalog) {
  const components = Object.entries(normalizeCatalog(catalog)).map(([name, value]) => ({ name, ...value }));
  const mappings = [];
  let id = 1;
  walkDom(serialized.dom, (node) => {
    const kind = elementKind(node);
    if (!kind) return;
    const ranked = components
      .map((component) => ({ component, score: scoreCandidate(kind, node, component) }))
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score);

    mappings.push({
      id,
      source: {
        tag: node.tag,
        kind,
        classes: node.classes || [],
        attrs: node.attrs || {},
      },
      candidate:
        ranked[0] && ranked[0].score >= 50
          ? {
              name: ranked[0].component.name,
              path: ranked[0].component.path,
              confidence: ranked[0].score,
              props: ranked[0].component.props || [],
            }
          : null,
      fallback: ranked[0] ? "low-confidence-review-required" : "create-or-inline",
    });
    id += 1;
  });
  return mappings;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.serialized || !args["project-root"]) {
    console.error(
      "Usage: node component-mapping.js --serialized <serialized.json> --project-root <root> [--catalog <catalog.json>] [--architecture <architecture.json>] [--component-dirs <a,b>] [--out <path>]",
    );
    process.exit(1);
  }

  const projectRoot = path.resolve(args["project-root"]);
  const serialized = JSON.parse(fs.readFileSync(path.resolve(args.serialized), "utf8"));
  const explicitCatalog = readJsonIfExists(args.catalog ? path.resolve(args.catalog) : null);
  const componentDirs = args["component-dirs"]
    ? args["component-dirs"].split(",").map((value) => value.trim()).filter(Boolean)
    : null;
  const catalog =
    explicitCatalog ||
    buildCatalog(projectRoot, {
      componentDirs,
      architecturePath: args.architecture ? path.resolve(args.architecture) : null,
    });
  const result = {
    generatedAt: new Date().toISOString(),
    projectRoot,
    catalog,
    mappings: mapDom(serialized, catalog),
  };

  const json = JSON.stringify(result, null, 2);
  if (args.out) fs.writeFileSync(path.resolve(args.out), `${json}\n`);
  else process.stdout.write(`${json}\n`);
}

if (require.main === module) main();

module.exports = { buildCatalog, mapDom };
