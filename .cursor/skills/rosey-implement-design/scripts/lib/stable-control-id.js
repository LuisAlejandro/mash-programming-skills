const crypto = require("crypto");

function normalizeText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 80);
}

function buildStableControlId({ kind, tag, attrs = {}, classes = [], pathSegments = [], text = "" }) {
  const parts = [
    kind,
    tag,
    attrs.id || "",
    attrs.name || "",
    attrs.role || "",
    attrs["aria-label"] || "",
    attrs.href || "",
    attrs.alt || "",
    attrs.placeholder || "",
    attrs.type || "",
    (classes || []).slice(0, 6).join("."),
    pathSegments.join(">"),
    normalizeText(text),
  ];
  const hash = crypto.createHash("sha256").update(parts.join("|")).digest("hex").slice(0, 12);
  return `${kind}-${hash}`;
}

function buildDomPathSegment(node, indexAmongSiblings) {
  const id = node.attrs?.id;
  if (id) return `${node.tag}#${id}`;
  const classes = (node.classes || []).slice(0, 2).join(".");
  return classes ? `${node.tag}.${classes}` : `${node.tag}:nth(${indexAmongSiblings})`;
}

module.exports = { buildStableControlId, buildDomPathSegment, normalizeText };
