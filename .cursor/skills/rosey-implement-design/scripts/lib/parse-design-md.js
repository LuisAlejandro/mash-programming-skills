function parseDesignMd(content) {
  const result = {
    title: "",
    category: "",
    description: "",
    sections: [],
    tokens: {
      colors: {},
      typography: {},
      spacing: {},
    },
  };

  const lines = content.split(/\r?\n/);
  let currentSection = null;

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trim();
    if (!line) continue;

    if (line.startsWith("# ")) {
      result.title = line.slice(2).trim();
      continue;
    }

    if (line.startsWith("> ")) {
      const quote = line.slice(2).trim();
      if (quote.startsWith("Category:")) {
        result.category = quote.slice(9).trim();
      } else {
        result.description = (result.description ? `${result.description}\n` : "") + quote;
      }
      continue;
    }

    if (line.startsWith("## ")) {
      currentSection = { title: line.slice(3).trim(), content: [], listItems: [] };
      result.sections.push(currentSection);
      continue;
    }

    if (currentSection) {
      if (line.startsWith("- ") || line.startsWith("* ")) {
        currentSection.listItems.push(line.slice(2).trim());
      } else {
        currentSection.content.push(line);
      }
    }
  }

  const cssVarRegex = /(--[A-Za-z0-9-_]+)\s*:\s*([^;]+);?/g;
  for (const match of content.matchAll(cssVarRegex)) {
    const name = match[1].toLowerCase();
    const value = match[2].trim();
    if (/color|bg|fill|stroke|brand|primary|secondary|accent/i.test(name)) {
      result.tokens.colors[name] = value;
    } else if (/font|line|letter|text/i.test(name)) {
      result.tokens.typography[name] = value;
    } else if (/space|gap|radius|size|padding|margin/i.test(name)) {
      result.tokens.spacing[name] = value;
    }
  }

  for (const section of result.sections) {
    const cleanTitle = section.title.toLowerCase();
    if (cleanTitle.includes("color")) {
      for (const item of section.listItems) {
        const match = item.match(/^([^:]+):\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|var\([^)]+\))/);
        if (match) {
          result.tokens.colors[match[1].trim().toLowerCase()] = match[2].trim();
        }
      }
      for (const line of section.content) {
        const inline = line.match(/^([^:]+):\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|var\([^)]+\))/);
        if (inline) result.tokens.colors[inline[1].trim().toLowerCase()] = inline[2].trim();
      }
    } else if (cleanTitle.includes("typography")) {
      for (const item of section.listItems) {
        const parts = item.split(":");
        if (parts.length >= 2) {
          result.tokens.typography[parts[0].trim().toLowerCase()] = parts.slice(1).join(":").trim();
        }
      }
    } else if (cleanTitle.includes("spacing")) {
      for (const item of section.listItems) {
        const parts = item.split(":");
        if (parts.length >= 2) {
          result.tokens.spacing[parts[0].trim().toLowerCase()] = parts.slice(1).join(":").trim();
        }
      }
    }
  }

  return result;
}

const fs = require("fs");
const path = require("path");

function findDesignMdPath({ designPath, htmlPath, projectRoot }) {
  if (designPath && fs.existsSync(designPath)) return designPath;
  const candidates = [];
  if (htmlPath) {
    candidates.push(path.join(path.dirname(htmlPath), "DESIGN.md"), path.join(path.dirname(htmlPath), "design.md"));
  }
  if (projectRoot) {
    candidates.push(
      path.join(projectRoot, "docs", "design-system", "DESIGN.md"),
      path.join(projectRoot, "docs", "design-system", "design.md"),
      path.join(projectRoot, "DESIGN.md"),
      path.join(projectRoot, "design.md"),
    );
  }
  for (const candidate of candidates) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
  }
  return null;
}

function loadDesignSystem(options = {}) {
  const resolvedPath = findDesignMdPath(options);
  if (!resolvedPath) return null;
  return { path: resolvedPath, ...parseDesignMd(fs.readFileSync(resolvedPath, "utf8")) };
}

module.exports = { parseDesignMd, findDesignMdPath, loadDesignSystem };
