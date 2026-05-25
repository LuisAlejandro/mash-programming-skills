#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const IGNORE_DIRS = new Set([".git", ".next", ".turbo", "node_modules", "dist", "build", "coverage"]);

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

function exists(root, relativePath) {
  return fs.existsSync(path.join(root, relativePath));
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function walk(root, predicate, results = []) {
  if (!fs.existsSync(root)) return results;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (IGNORE_DIRS.has(entry.name)) continue;
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) walk(fullPath, predicate, results);
    else if (predicate(fullPath)) results.push(fullPath);
  }
  return results;
}

function findPackageJsons(root) {
  return walk(root, (filePath) => path.basename(filePath) === "package.json");
}

function mergeDeps(packageJsons) {
  const deps = {};
  for (const packageJson of packageJsons) {
    const data = readJson(packageJson);
    Object.assign(deps, data?.dependencies || {}, data?.devDependencies || {});
  }
  return deps;
}

function detectFramework(root, deps) {
  if (exists(root, "next.config.js") || exists(root, "next.config.mjs") || deps.next) return "next";
  if (exists(root, "nuxt.config.ts") || exists(root, "nuxt.config.js") || deps.nuxt) return "nuxt";
  if (exists(root, "svelte.config.js") || deps["@sveltejs/kit"]) return "sveltekit";
  if (exists(root, "astro.config.mjs") || deps.astro) return "astro";
  if (exists(root, "angular.json") || deps["@angular/core"]) return "angular";
  if (exists(root, "vite.config.ts") || exists(root, "vite.config.js") || deps.vite) {
    if (deps.react) return "vite-react";
    if (deps.vue) return "vite-vue";
    if (deps.svelte) return "vite-svelte";
    return "vite";
  }
  if (deps.react) return "react";
  if (deps.vue) return "vue";
  return "unknown";
}

function detectStyling(root, deps) {
  const styles = [];
  if (exists(root, "tailwind.config.js") || exists(root, "tailwind.config.ts") || deps.tailwindcss || deps["@tailwindcss/vite"]) {
    styles.push("tailwind");
  }
  const styleFiles = walk(root, (filePath) => /\.(css|scss|sass|less|tsx|jsx)$/.test(filePath));
  if (styleFiles.some((filePath) => /\.module\.(css|scss|sass)$/.test(filePath))) styles.push("css-modules");
  if (deps["styled-components"]) styles.push("styled-components");
  if (deps["@emotion/react"] || deps["@emotion/styled"]) styles.push("emotion");
  if (styleFiles.some((filePath) => /\.(scss|sass)$/.test(filePath))) styles.push("sass");
  if (styleFiles.some((filePath) => /\.css$/.test(filePath))) styles.push("css");
  return Array.from(new Set(styles));
}

function existingDirs(root, candidates) {
  return candidates.filter((relativePath) => fs.existsSync(path.join(root, relativePath)));
}

function findTokenFiles(root) {
  return walk(root, (filePath) => {
    const base = path.basename(filePath).toLowerCase();
    return /(token|theme|variable|design-system)/.test(base) && /\.(css|scss|sass|ts|js|json)$/.test(base);
  }).map((filePath) => path.relative(root, filePath));
}

function detectScripts(packageJsons) {
  const scripts = {};
  for (const packageJson of packageJsons) {
    const data = readJson(packageJson);
    if (!data?.scripts) continue;
    scripts[path.relative(process.cwd(), packageJson)] = data.scripts;
  }
  return scripts;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = path.resolve(args.root || process.cwd());
  const packageJsons = findPackageJsons(root);
  const deps = mergeDeps(packageJsons);
  const result = {
    root,
    framework: detectFramework(root, deps),
    styling: detectStyling(root, deps),
    packageJsons: packageJsons.map((filePath) => path.relative(root, filePath)),
    componentDirs: existingDirs(root, [
      "src/components",
      "app/components",
      "components",
      "src/ui",
      "lib/components",
      "packages/ui",
      "packages/design-system",
    ]),
    routeDirs: existingDirs(root, ["app", "pages", "src/pages", "src/routes", "src/views"]),
    assetDirs: existingDirs(root, ["public", "static", "src/assets", "public/assets", "public/images"]),
    tokenFiles: findTokenFiles(root),
    scripts: detectScripts(packageJsons),
    aliases: {
      tsconfig: exists(root, "tsconfig.json") ? "tsconfig.json" : null,
      jsconfig: exists(root, "jsconfig.json") ? "jsconfig.json" : null,
    },
  };

  const json = JSON.stringify(result, null, 2);
  if (args.out) fs.writeFileSync(path.resolve(args.out), `${json}\n`);
  else process.stdout.write(`${json}\n`);
}

if (require.main === module) main();
