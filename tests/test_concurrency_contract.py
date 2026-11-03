"""U9: the corpus-wide concurrency contract.

The behavioural guarantees live in `src/skills/mash-workspace/tests/`. These
tests guard the part that code cannot enforce: that the skills' own
instructions still describe the safe procedure. Prose drifts silently, so each
rule here corresponds to a hazard that was reproduced before the fix.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "src" / "skills"
RULES = ROOT / "src" / "rules"

sys.path.insert(0, str(SKILLS / "mash-workspace" / "scripts"))
import workspace as ws

# Skills that run a workflow against the repository and therefore contend with
# other runs. Loader skills and advisory skills are deliberately excluded.
WORKFLOW_SKILLS = (
    "mash-brainstorm", "mash-plan", "mash-work", "mash-qa", "mash-lint",
    "mash-pr", "mash-debug", "mash-parallel", "mash-dogfood", "mash-release",
)


def skill_docs(name):
    """SKILL.md plus every reference file for one skill."""
    root = SKILLS / name
    return sorted(root.rglob("*.md"))


def corpus_docs():
    for path in sorted(SKILLS.rglob("*.md")):
        if "/tests/" not in str(path):
            yield path
    yield from sorted(RULES.glob("*.mdc"))


class StashIsGone(unittest.TestCase):
    """The stash is one shared stack: concurrent runs popped each other's work."""

    def test_no_skill_instructs_a_stash(self):
        offenders = []
        for path in corpus_docs():
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if re.search(r"\bgit stash\b", line) and "never" not in line.lower():
                    offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
        self.assertEqual(offenders, [], "git stash must not be instructed:\n" + "\n".join(offenders))

    def test_the_helper_no_longer_offers_stash_subcommands(self):
        helper = (SKILLS / "mash-brainstorm" / "scripts" / "feature_worktree.py").read_text()
        self.assertNotIn("stash-apply", helper)
        self.assertNotIn("stash-drop", helper)

    def test_shipping_documents_the_transfer_replacement(self):
        text = (SKILLS / "mash-pr" / "references" / "branch-creation.md").read_text()
        self.assertIn("transfer", text)
        self.assertIn("FILES_CHANGED", text)


class RunIdentityIsDocumented(unittest.TestCase):
    """A workflow that cannot name its run cannot own anything."""

    def test_every_workflow_skill_points_at_the_workspace_contract(self):
        missing = [
            name for name in WORKFLOW_SKILLS
            if not any("mash-workspace" in path.read_text() for path in skill_docs(name))
        ]
        self.assertEqual(missing, [], f"skills with no workspace contract: {missing}")

    def test_the_contract_skill_exists_and_states_its_guarantee(self):
        text = (SKILLS / "mash-workspace" / "SKILL.md").read_text()
        for required in ("Guarantee", "non-guarantee", "lease", "run"):
            self.assertIn(required, text)

    def test_every_lease_kind_is_documented(self):
        text = (SKILLS / "mash-workspace" / "SKILL.md").read_text()
        undocumented = [kind for kind in ws.LEASE_KINDS if kind not in text]
        self.assertEqual(undocumented, [], f"undocumented lease kinds: {undocumented}")


class SharedResourcesAreClaimed(unittest.TestCase):
    """Ports, browsers and the release pipeline are machine-wide, not per-run."""

    def test_skills_that_start_services_document_a_claim(self):
        for name in ("mash-dogfood",):
            text = "\n".join(path.read_text() for path in skill_docs(name))
            self.assertIn("lease acquire", text, f"{name} starts services without claiming them")

    def test_release_documents_an_exclusive_claim(self):
        text = "\n".join(path.read_text() for path in skill_docs("mash-release"))
        self.assertIn("--kind release", text)


class WorkspacesAreOwned(unittest.TestCase):
    """A workspace reused by slug handed one run another run's working tree."""

    def test_allowlist_has_one_definition(self):
        sys.path.insert(0, str(SKILLS / "mash-parallel" / "scripts"))
        sys.path.insert(0, str(SKILLS / "mash-brainstorm" / "scripts"))
        import feature_worktree as fw
        import mash_parallel as mp

        self.assertEqual(ws.RUNTIME_FILE_ALLOWLIST, mp.RUNTIME_FILE_ALLOWLIST)
        self.assertIs(fw.RUNTIME_FILE_ALLOWLIST, ws.RUNTIME_FILE_ALLOWLIST)

    def test_integration_workspace_is_not_a_shared_path(self):
        source = (SKILLS / "mash-parallel" / "scripts" / "mash_parallel.py").read_text()
        self.assertNotIn('repo / "mash-parallel-integration"', source)
        self.assertIn('run_dir(repo, owner) / "integration"', source)

    def test_base_publication_uses_compare_and_swap(self):
        source = (SKILLS / "mash-parallel" / "scripts" / "mash_parallel.py").read_text()
        self.assertIn("base_before", source)
        self.assertRegex(source, r'"update-ref", base_ref, integrated_tip, base_before')


class BlockersAreActionable(unittest.TestCase):
    """Fail fast was chosen over waiting, so a refusal must say what to do."""

    def test_refusals_carry_recovery_steps(self):
        source = (SKILLS / "mash-workspace" / "scripts" / "workspace.py").read_text()
        self.assertIn('"recovery"', source)
        self.assertIn('"holder"', source)

    def test_the_contract_documents_the_fail_fast_choice(self):
        text = (SKILLS / "mash-workspace" / "SKILL.md").read_text()
        self.assertIn("Exit `2`", text)
        self.assertIn("fails fast", text.lower())


if __name__ == "__main__":
    unittest.main()
