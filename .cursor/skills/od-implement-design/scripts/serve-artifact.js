#!/usr/bin/env node

const fs = require("fs");
const http = require("http");
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

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
  }[ext] || "application/octet-stream";
}

function safeResolve(root, requestPath) {
  const cleaned = decodeURIComponent(requestPath.split("?")[0]).replace(/^\/+/, "");
  const target = cleaned === "" ? root : path.resolve(root, cleaned);
  if (!target.startsWith(root)) return null;
  return target;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.html) {
    console.error("Usage: node serve-artifact.js --html <path> [--assets-dir <dir>] [--port <port>]");
    process.exit(1);
  }

  const htmlPath = path.resolve(args.html);
  if (!fs.existsSync(htmlPath) || !fs.statSync(htmlPath).isFile()) {
    console.error(`HTML artifact not found: ${htmlPath}`);
    process.exit(1);
  }

  const root = path.resolve(args["assets-dir"] || path.dirname(htmlPath));
  const port = Number(args.port || 0);
  const htmlFile = path.basename(htmlPath);
  const server = http.createServer((request, response) => {
    const requested = request.url === "/" ? htmlFile : request.url;
    const target = safeResolve(root, requested);
    if (!target || !fs.existsSync(target) || !fs.statSync(target).isFile()) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": contentType(target) });
    fs.createReadStream(target).pipe(response);
  });

  server.listen(port, "127.0.0.1", () => {
    const address = server.address();
    process.stdout.write(`OD_ARTIFACT_URL=http://127.0.0.1:${address.port}/\n`);
  });
}

if (require.main === module) main();
