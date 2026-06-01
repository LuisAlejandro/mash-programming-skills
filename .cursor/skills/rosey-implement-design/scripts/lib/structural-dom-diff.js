function fingerprint(item) {
  return [
    item.stableId || "",
    item.tag,
    item.role || "",
    item.id || "",
    (item.classes || []).join("."),
    normalizeText(item.text),
  ].join("|");
}

function normalizeText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 80);
}

function similarity(a, b) {
  if (a.stableId && b.stableId && a.stableId === b.stableId) return 1;
  let score = 0;
  if (a.tag === b.tag) score += 0.35;
  if ((a.role || null) === (b.role || null)) score += 0.2;
  if ((a.id || null) && a.id === b.id) score += 0.25;
  const aClasses = new Set(a.classes || []);
  const bClasses = new Set(b.classes || []);
  const sharedClasses = [...aClasses].filter((c) => bClasses.has(c));
  if (sharedClasses.length > 0) score += Math.min(0.15, sharedClasses.length * 0.05);
  if (normalizeText(a.text) && normalizeText(a.text) === normalizeText(b.text)) score += 0.2;
  return score;
}

function compareStructuralDom(baseline, target, options = {}) {
  const minScore = options.minScore ?? 0.55;
  const usedTarget = new Set();
  const findings = [];

  for (const a of baseline) {
    let bestIndex = -1;
    let bestScore = 0;
    for (let j = 0; j < target.length; j += 1) {
      if (usedTarget.has(j)) continue;
      const score = similarity(a, target[j]);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = j;
      }
    }

    if (bestIndex === -1 || bestScore < minScore) {
      findings.push({
        id: `dom-missing-${a.stableId || a.tag}-${findings.length}`,
        severity: "major",
        element: a.stableId || `${a.tag}@${a.depth}`,
        expected: fingerprint(a),
        observed: "missing",
        recommendation: "Add or restore the baseline control in the implementation.",
        stableId: a.stableId || null,
      });
      continue;
    }

    usedTarget.add(bestIndex);
    const b = target[bestIndex];

    if (a.tag !== b.tag || (a.role || null) !== (b.role || null)) {
      findings.push({
        id: `dom-mismatch-${a.stableId || a.tag}-${findings.length}`,
        severity: "blocking",
        element: a.stableId || `${a.tag}@${a.depth}`,
        expected: `${a.tag}${a.role ? `[role=${a.role}]` : ""}`,
        observed: `${b.tag}${b.role ? `[role=${b.role}]` : ""}`,
        recommendation: "Match semantic tag and ARIA role to the baseline control.",
        stableId: a.stableId || null,
      });
      continue;
    }

    if (Math.abs((a.depth || 0) - (b.depth || 0)) > 2) {
      findings.push({
        id: `dom-wrapper-${a.stableId || a.tag}-${findings.length}`,
        severity: "minor",
        element: a.stableId || `${a.tag}@${a.depth}`,
        expected: `depth ${a.depth}`,
        observed: `depth ${b.depth}`,
        recommendation: "Wrapper depth differs; verify layout only if visuals regress.",
        stableId: a.stableId || null,
      });
    }
  }

  for (let j = 0; j < target.length; j += 1) {
    if (usedTarget.has(j)) continue;
    const b = target[j];
    findings.push({
      id: `dom-extra-${b.stableId || b.tag}-${findings.length}`,
      severity: "major",
      element: b.stableId || `${b.tag}@${b.depth}`,
      expected: "absent",
      observed: fingerprint(b),
      recommendation: "Remove extra DOM nodes not present in the baseline.",
      stableId: b.stableId || null,
    });
  }

  return findings;
}

module.exports = { compareStructuralDom, fingerprint, similarity };
