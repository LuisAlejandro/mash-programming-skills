const path = require("path");

let babelParser;
let babelTraverse;
try {
  babelParser = require("@babel/parser");
  babelTraverse = require("@babel/traverse").default;
} catch {
  babelParser = null;
}

const BABEL_PLUGINS = ["jsx", "typescript", "decorators-legacy", "classProperties"];

function parseWithBabel(content, filePath) {
  if (!babelParser) return null;
  const isTypeScript = /\.tsx?$/.test(filePath);
  try {
    return babelParser.parse(content, {
      sourceType: "module",
      plugins: isTypeScript ? BABEL_PLUGINS : ["jsx", "decorators-legacy", "classProperties"],
      errorRecovery: true,
    });
  } catch {
    return null;
  }
}

function extractExportsRegex(content, filePath) {
  const names = new Set();
  const patterns = [
    /export\s+default\s+function\s+([A-Z][A-Za-z0-9_]*)/g,
    /export\s+default\s+([A-Z][A-Za-z0-9_]*)/g,
    /export\s+function\s+([A-Z][A-Za-z0-9_]*)/g,
    /export\s+(?:const|let|var|class)\s+([A-Z][A-Za-z0-9_]*)/g,
    /export\s*{\s*([A-Z][A-Za-z0-9_]*)\s*(?:,|\})/g,
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

function extractExportsAst(content, filePath) {
  const ast = parseWithBabel(content, filePath);
  if (!ast || !babelTraverse) return null;

  const names = new Set();

  babelTraverse(ast, {
    ExportDefaultDeclaration(pathNode) {
      const decl = pathNode.node.declaration;
      if (decl.id?.name) names.add(decl.id.name);
      else if (decl.type === "Identifier") names.add(decl.name);
      else if (decl.type === "FunctionDeclaration" && decl.id?.name) names.add(decl.id.name);
    },
    ExportNamedDeclaration(pathNode) {
      const decl = pathNode.node.declaration;
      if (decl?.id?.name && /^[A-Z]/.test(decl.id.name)) names.add(decl.id.name);
      if (decl?.declarations) {
        for (const d of decl.declarations) {
          if (d.id?.name && /^[A-Z]/.test(d.id.name)) names.add(d.id.name);
        }
      }
      for (const spec of pathNode.node.specifiers || []) {
        const exported = spec.exported?.name || spec.exported?.value;
        if (exported && /^[A-Z]/.test(exported)) names.add(exported);
      }
    },
  });

  return names.size > 0 ? Array.from(names) : null;
}

function extractPropsAst(content, filePath, componentName) {
  const ast = parseWithBabel(content, filePath);
  if (!ast || !babelTraverse) return null;

  const props = new Set();
  const propsTypeName = `${componentName}Props`;

  babelTraverse(ast, {
    TSInterfaceDeclaration(pathNode) {
      if (pathNode.node.id.name !== propsTypeName) return;
      for (const member of pathNode.node.body.body) {
        if (member.key?.name) props.add(member.key.name);
      }
    },
    TSTypeAliasDeclaration(pathNode) {
      if (pathNode.node.id.name !== propsTypeName) return;
      if (pathNode.node.typeAnnotation?.type === "TSTypeLiteral") {
        for (const member of pathNode.node.typeAnnotation.members) {
          if (member.key?.name) props.add(member.key.name);
        }
      }
    },
    FunctionDeclaration(pathNode) {
      if (pathNode.node.id?.name !== componentName) return;
      const first = pathNode.node.params[0];
      if (first?.type === "ObjectPattern") {
        for (const prop of first.properties) {
          if (prop.key?.name && !["className", "children", "ref"].includes(prop.key.name)) props.add(prop.key.name);
        }
      }
    },
    VariableDeclarator(pathNode) {
      if (pathNode.node.id?.name !== componentName) return;
      const init = pathNode.node.init;
      if (init?.type === "ArrowFunctionExpression" && init.params[0]?.type === "ObjectPattern") {
        for (const prop of init.params[0].properties) {
          if (prop.key?.name && !["className", "children", "ref"].includes(prop.key.name)) props.add(prop.key.name);
        }
      }
    },
  });

  return props.size > 0 ? Array.from(props) : null;
}

function extractPropsRegex(content, componentName) {
  const props = new Set();
  const escapedName = componentName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const specificInterface = content.match(
    new RegExp(`interface\\s+${escapedName}Props(?:\\s+extends\\s+([^{]+))?\\s*{([\\s\\S]*?)}`),
  );
  const body = specificInterface?.[2] || "";
  const propRegex = /([A-Za-z_$][A-Za-z0-9_$]*)\??\s*:/g;
  let match;
  while ((match = propRegex.exec(body))) props.add(match[1]);
  return Array.from(props);
}

function extractExports(content, filePath) {
  if (/\.(vue|svelte)$/.test(filePath)) return extractExportsRegex(content, filePath);
  return extractExportsAst(content, filePath) || extractExportsRegex(content, filePath);
}

function extractProps(content, filePath, componentName) {
  if (/\.(vue|svelte)$/.test(filePath)) return extractPropsRegex(content, componentName);
  return extractPropsAst(content, filePath, componentName) || extractPropsRegex(content, componentName);
}

module.exports = { extractExports, extractProps };
