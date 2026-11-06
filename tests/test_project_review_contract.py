"""Contract for the phase-1 project self-review skills.

These tests guard the instructions an agent will follow. They do not run ZAP
or a browser.
"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "src" / "skills"
KIT = ("mash-project-review", "mash-a11y", "mash-web-security")
CLAIM_PHRASES = ("WCAG compliant", "ASVS compliant", "OWASP-safe")
STATUSES = (
    "Pending",
    "Pass",
    "Fail",
    "Skipped",
    "Blocked (needs human verify)",
)


def skill_tree(name):
    return sorted((SKILLS / name).rglob("*.md"))


def combined(names):
    parts = []
    for name in names:
        parts.extend(path.read_text() for path in skill_tree(name))
    return "\n".join(parts)


class ProjectReviewContractTest(unittest.TestCase):
    def test_skill_folders_and_frontmatter_exist(self):
        for name in KIT:
            skill = SKILLS / name / "SKILL.md"
            self.assertTrue(skill.is_file(), name)
            frontmatter = skill.read_text().split("---", 2)[1]
            self.assertIn(f"name: {name}", frontmatter)
            self.assertIn("description:", frontmatter)
            self.assertNotIn("/mash-", frontmatter)
            self.assertNotIn("/skill:", frontmatter)

    def test_report_template_lists_required_statuses(self):
        template = (
            SKILLS / "mash-project-review" / "references" / "report-template.md"
        ).read_text()
        for status in STATUSES:
            self.assertIn(status, template)
        vocabulary = (
            SKILLS / "mash-project-review" / "references" / "status-vocabulary.md"
        ).read_text()
        for status in STATUSES:
            self.assertIn(f"`{status}`", vocabulary)

    def test_compliance_claims_only_appear_as_refusals(self):
        for path in skill_tree("mash-project-review") + skill_tree("mash-a11y") + skill_tree(
            "mash-web-security"
        ):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                for phrase in CLAIM_PHRASES:
                    if phrase.lower() in line.lower():
                        self.assertRegex(
                            line,
                            r"\b([Nn]ever|[Nn]ot|do not|Do not)\b",
                            f"{path.relative_to(ROOT)}:{number} states {phrase} without a refusal",
                        )
        text = combined(KIT)
        self.assertIn("Never claim the target is WCAG compliant", text)
        self.assertIn("ASVS compliant", text)
        self.assertIn("OWASP-safe", text)

    def test_production_targets_are_refused(self):
        text = combined(KIT)
        self.assertIn("target:prod", text)
        self.assertRegex(text, r"[Rr]efus")
        self.assertNotRegex(text, r"[Dd]efault[^\n]{0,80}target:prod")
        self.assertNotRegex(text, r"target:prod[^\n]{0,80}default")
        safety = (
            SKILLS / "mash-project-review" / "references" / "safety.md"
        ).read_text()
        self.assertIn("target:local", safety)
        self.assertIn("Production targets are refused", safety)

    def test_fronts_use_the_shared_evidence_rules(self):
        evidence = (
            SKILLS / "mash-project-review" / "references" / "evidence.md"
        ).read_text()
        self.assertIn("MASH_EVIDENCE", evidence)
        self.assertIn("END_MASH_EVIDENCE", evidence)
        self.assertIn("$ <exact command>", evidence)
        for name in KIT:
            text = (SKILLS / name / "SKILL.md").read_text()
            self.assertIn("MASH_EVIDENCE", text)
            self.assertIn("END_MASH_EVIDENCE", text)
        for name in ("mash-a11y", "mash-web-security"):
            text = (SKILLS / name / "SKILL.md").read_text()
            self.assertIn("mash-project-review", text)

    def test_skills_do_not_instruct_git_stash_or_slash_invocation(self):
        for path in skill_tree("mash-project-review") + skill_tree("mash-a11y") + skill_tree(
            "mash-web-security"
        ):
            text = path.read_text()
            # A temp path such as ${TMPDIR:-/tmp}/mash-project-review contains the
            # characters "/mash-" without being a slash invocation.
            self.assertNotRegex(text, r"(^|[\s`])/(mash-|skill:)", path)
            for number, line in enumerate(text.splitlines(), 1):
                if re.search(r"\bgit stash\b", line) and "never" not in line.lower():
                    self.fail(f"{path.relative_to(ROOT)}:{number} instructs git stash")

    def test_axe_runner_is_skill_local_and_not_a_second_browser(self):
        package = json.loads((SKILLS / "mash-a11y" / "package.json").read_text())
        self.assertEqual(package["name"], "mash-a11y")
        self.assertIn("axe-core", package["dependencies"])
        self.assertNotIn("puppeteer", package.get("dependencies", {}))
        self.assertNotIn("playwright", package.get("dependencies", {}))
        runner = (SKILLS / "mash-a11y" / "scripts" / "run_axe.mjs").read_text()
        self.assertIn("axe-core", runner)
        self.assertIn("AXE_JSON", runner)
        self.assertNotIn("npx", runner)
        self.assertNotIn("puppeteer", runner)
        skill = (SKILLS / "mash-a11y" / "SKILL.md").read_text()
        self.assertIn("Do not shell out to `npx`", skill)
        self.assertIn("chrome-devtools", skill)

    def test_axe_self_check_when_node_and_deps_are_present(self):
        modules = SKILLS / "mash-a11y" / "node_modules" / "axe-core"
        if shutil.which("node") is None or not modules.is_dir():
            self.skipTest("axe-core is installed by the Mash skill dependency step")
        completed = subprocess.run(
            [
                "node",
                str(SKILLS / "mash-a11y" / "scripts" / "run_axe.mjs"),
                "--self-check",
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("self-check ok", completed.stdout)


if __name__ == "__main__":
    unittest.main()
