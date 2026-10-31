import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "src" / "skills"


def skill_text(name):
    return (SKILLS / name / "SKILL.md").read_text()


class AutomationLayerTest(unittest.TestCase):
    def test_routing_skills_match_their_directories(self):
        for name in ("cua-driver", "agent-browser", "chrome-devtools"):
            text = skill_text(name)
            frontmatter = text.split("---", 2)[1]
            self.assertIn(f"name: {name}", frontmatter)
            self.assertNotIn("cua do", text)
            self.assertNotIn("gui-automation", text)

    def test_cua_skill_stops_for_a_missing_grant(self):
        text = skill_text("cua-driver")
        self.assertIn("Accessibility", text)
        self.assertIn("Screen Recording", text)
        self.assertIn("stop", text.lower())
        self.assertNotIn("KeepAlive", text)

    def test_agent_browser_skill_requires_a_named_isolated_session(self):
        text = skill_text("agent-browser")
        self.assertIn("named session", text.lower())
        self.assertIn("Default", text)
        self.assertIn("auto-connect", text)

    def test_auth_wall_handoff_is_human_first_and_platform_qualified(self):
        text = skill_text("agent-browser")
        self.assertIn("dedicated, non-default profile", text)
        self.assertIn("Never attach to this window", text)
        self.assertIn("permits the session to be automated", text)
        self.assertIn("macOS example only", text)
        self.assertIn("On Linux or Windows", text)
        self.assertIn("agent-browser --session auth-handoff connect 9222", text)
        self.assertIn("--remote-debugging-address=127.0.0.1", text)
        self.assertIn("read the response body", text)
        self.assertNotIn("cookies are encrypted to the binary", text)
        self.assertNotIn("whenever automation is attached", text)
        self.assertNotIn("a challenge cannot be passed", text)

    def test_auth_wall_guidance_stays_in_the_browser_skill(self):
        rule = (ROOT / "src/rules/browser-desktop-automation.mdc").read_text()
        self.assertIn("human sign-in handoff in the `agent-browser` skill", rule)
        self.assertNotIn("real-Chrome binary path", rule)
        self.assertNotIn("Mash.app", rule)

    def test_chrome_devtools_skill_leaves_page_journeys_on_agent_browser(self):
        text = skill_text("chrome-devtools")
        self.assertIn("Ordinary page journeys stay on agent-browser", text)

    def test_dogfood_uses_agent_browser_evidence(self):
        browser = (SKILLS / "mash-dogfood" / "references" / "browser.md").read_text()
        skill = (SKILLS / "mash-dogfood" / "SKILL.md").read_text()
        phases = (SKILLS / "mash-dogfood" / "references" / "phases.md").read_text()
        self.assertIn("agent-browser", browser)
        self.assertIn("screenshot", browser.lower())
        self.assertIn("console", browser.lower())
        self.assertIn("network", browser.lower())
        self.assertNotIn("Never `agent-browser`", browser)
        self.assertNotIn("never `agent-browser`", skill)
        self.assertNotIn("host's browser tools", phases)
        self.assertIn("references/browser.md", phases)
        combined = browser + skill
        self.assertNotIn("attach to the human's default Chrome profile and continue", combined)
        self.assertIn("default Chrome profile", combined)

    def test_debug_stops_when_agent_browser_is_missing(self):
        text = skill_text("mash-debug")
        self.assertIn("agent-browser", text)
        self.assertIn("stop", text.lower())
        self.assertNotIn("whatever works", text)


if __name__ == "__main__":
    unittest.main()
