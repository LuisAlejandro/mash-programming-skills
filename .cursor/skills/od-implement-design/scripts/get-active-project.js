#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

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

function readManifest(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return {};
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function inferName(htmlPath, manifest) {
  if (manifest.name) return manifest.name;
  if (!htmlPath) return "opendesign-artifact";
  return path.basename(htmlPath).replace(/\.[^.]+$/, "");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifestPath = args.manifest ? path.resolve(args.manifest) : null;
  const manifest = readManifest(manifestPath);
  const rawHtmlPath = args.html || manifest.htmlPath || manifest.source?.htmlPath;

  if (!rawHtmlPath) {
    console.error("Usage: node get-active-project.js --html <path> [--manifest <path>] [--preview-url <url>] [--assets-dir <path>]");
    process.exit(1);
  }

  const htmlPath = path.resolve(rawHtmlPath);
  const stat = fs.existsSync(htmlPath) ? fs.statSync(htmlPath) : null;
  if (!stat || !stat.isFile() || !/\.(html|htm)$/i.test(htmlPath)) {
    console.error(`OpenDesign artifact must be an existing .html/.htm file: ${htmlPath}`);
    process.exit(1);
  }

  const result = {
    name: inferName(htmlPath, manifest),
    source: "opendesign-export",
    htmlPath,
    previewUrl: args["preview-url"] || manifest.previewUrl || null,
    assetsDir: args["assets-dir"]
      ? path.resolve(args["assets-dir"])
      : manifest.assetsDir
        ? path.resolve(manifest.assetsDir)
        : null,
    manifestPath,
  };

  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (require.main === module) main();
