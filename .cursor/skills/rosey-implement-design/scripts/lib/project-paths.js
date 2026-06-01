const fs = require("fs");
const path = require("path");

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function loadPathAliases(projectRoot) {
  const aliases = {};
  for (const configName of ["tsconfig.json", "jsconfig.json"]) {
    const configPath = path.join(projectRoot, configName);
    const config = readJsonSafe(configPath);
    if (!config) continue;
    const baseUrl = config.compilerOptions?.baseUrl || ".";
    const paths = config.compilerOptions?.paths || {};
    for (const [alias, targets] of Object.entries(paths)) {
      const key = alias.replace(/\/?\*$/, "");
      const target = (Array.isArray(targets) ? targets[0] : targets).replace(/\/?\*$/, "");
      aliases[key] = path.resolve(projectRoot, baseUrl, target);
    }
  }
  return aliases;
}

function resolveAliasImport(componentPath, projectRoot, aliases) {
  const componentAbs = path.resolve(projectRoot, componentPath);
  const withoutExt = componentAbs.replace(/\.(tsx|jsx|ts|js|vue|svelte)$/, "");
  for (const [alias, targetDir] of Object.entries(aliases)) {
    if (withoutExt.startsWith(targetDir)) {
      const suffix = path.relative(targetDir, withoutExt).replace(/\\/g, "/");
      return `${alias}/${suffix}`;
    }
  }
  return null;
}

function computeImportPath(fromFile, componentPath, projectRoot, aliases = {}) {
  const fromDir = path.dirname(path.resolve(projectRoot, fromFile));
  const componentAbs = path.resolve(projectRoot, componentPath);
  const withoutExt = componentAbs.replace(/\.(tsx|jsx|ts|js|vue|svelte)$/, "");

  for (const [alias, targetDir] of Object.entries(aliases)) {
    if (withoutExt.startsWith(targetDir)) {
      const suffix = path.relative(targetDir, withoutExt).replace(/\\/g, "/");
      return `${alias}/${suffix}`;
    }
  }

  let relative = path.relative(fromDir, withoutExt).replace(/\\/g, "/");
  if (!relative.startsWith(".")) relative = `./${relative}`;
  return relative;
}

module.exports = {
  loadPathAliases,
  computeImportPath,
  resolveAliasImport,
};
