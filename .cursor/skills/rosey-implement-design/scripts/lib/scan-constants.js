/** Directories excluded from project architecture scans and token walks. */
const ROSEY_IGNORE_DIRS = new Set([
  ".git",
  ".next",
  ".turbo",
  "node_modules",
  "dist",
  "build",
  "coverage",
  ".cursor",
]);

module.exports = { ROSEY_IGNORE_DIRS };
