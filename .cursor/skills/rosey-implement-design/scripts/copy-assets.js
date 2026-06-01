#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { loadLatestRosey, readJsonIfExists, assertHtmlFresh, pageDir } = require("./lib/rosey-paths");

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

function resolveAssetDirs(projectRoot, architecture) {
  const candidates = architecture?.assetDirs || ["public", "static", "src/assets", "public/assets"];
  return candidates
    .map((dir) => path.resolve(projectRoot, dir))
    .filter((dir) => fs.existsSync(dir) && fs.statSync(dir).isDirectory());
}

function copyFile(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function assetReferenceFor(projectRoot, destRoot, dest) {
  const relToProject = path.relative(projectRoot, dest).replace(/\\/g, "/");
  const relToDest = path.relative(destRoot, dest).replace(/\\/g, "/");
  if (relToProject === relToDest || relToProject.startsWith("public/")) {
    return `/${relToDest}`;
  }
  return relToProject;
}

function destinationForAsset(src, serialized, destRoot) {
  const baseDir = serialized.source?.assetsDir || path.dirname(serialized.source?.htmlPath || src);
  let rel = path.relative(baseDir, src);
  if (rel.startsWith("..") || path.isAbsolute(rel)) rel = path.basename(src);
  const parsed = path.parse(rel);
  const hash = crypto.createHash("sha1").update(src).digest("hex").slice(0, 8);
  const safeDir = parsed.dir.split(path.sep).filter(Boolean).join(path.sep);
  const safeName = `${parsed.name}-${hash}${parsed.ext}`;
  return path.join(destRoot, "opendesign", safeDir, safeName);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args["project-root"]) {
    console.error(
      "Usage: node copy-assets.js --project-root <root> [--page-slug <slug>] [--context <path>] [--dest <dir>] [--dry-run]",
    );
    process.exit(1);
  }

  const projectRoot = path.resolve(args["project-root"]);
  let context = null;
  let pageSlug = args["page-slug"] || null;

  if (args.context) {
    context = readJsonIfExists(path.resolve(args.context));
  } else {
    try {
      const latest = loadLatestRosey(projectRoot, pageSlug);
      pageSlug = latest.pageSlug;
      context = readJsonIfExists(latest.contextPathAbs);
    } catch (error) {
      console.error(error.message);
      process.exit(1);
    }
  }

  const serialized = context?.serialized;
  const outPath =
    args.out ? path.resolve(args.out) : pageSlug ? path.join(pageDir(projectRoot, pageSlug), "asset-map.json") : null;

  if (!serialized?.assets?.length) {
    if (outPath && !args["dry-run"]) {
      fs.mkdirSync(path.dirname(outPath), { recursive: true });
      fs.writeFileSync(outPath, "{}\n");
    }
    process.stdout.write(
      `${JSON.stringify(
        {
          copied: [],
          skipped: [],
          message: "No assets to copy",
          assetMapPath: outPath && !args["dry-run"] ? path.relative(projectRoot, outPath) : null,
        },
        null,
        2,
      )}\n`,
    );
    return;
  }

  const htmlPath = context.artifact?.htmlPath || serialized.source?.htmlPath;
  if (htmlPath) assertHtmlFresh(context, htmlPath);

  const architecture = context?.architecture || {};
  const assetDirs = resolveAssetDirs(projectRoot, architecture);
  const destRoot = args.dest ? path.resolve(args.dest) : assetDirs[0] || path.resolve(projectRoot, "public");

  const copied = [];
  const skipped = [];
  const assetMap = {};

  for (const asset of serialized.assets) {
    const src = asset.resolvedPath;
    if (!src || !fs.existsSync(src) || !fs.statSync(src).isFile()) {
      skipped.push({ ref: asset.ref, reason: "source-missing" });
      continue;
    }
    const dest = destinationForAsset(src, serialized, destRoot);
    const assetRef = assetReferenceFor(projectRoot, destRoot, dest);
    if (args["dry-run"]) {
      copied.push({ ref: asset.ref, from: src, to: dest, assetRef });
      assetMap[asset.ref] = assetRef;
      continue;
    }
    copyFile(src, dest);
    copied.push({ ref: asset.ref, from: src, to: path.relative(projectRoot, dest), assetRef });
    assetMap[asset.ref] = assetRef;
  }

  if (outPath && !args["dry-run"]) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, `${JSON.stringify(assetMap, null, 2)}\n`);
  }

  process.stdout.write(
    `${JSON.stringify(
      {
        destRoot: path.relative(projectRoot, destRoot),
        assetMapPath: outPath && !args["dry-run"] ? path.relative(projectRoot, outPath) : null,
        dryRun: Boolean(args["dry-run"]),
        assetMap: args["dry-run"] ? assetMap : outPath ? assetMap : {},
        copied,
        skipped,
      },
      null,
      2,
    )}\n`,
  );
}

if (require.main === module) main();
