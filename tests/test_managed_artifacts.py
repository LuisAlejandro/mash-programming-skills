import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "managed_artifacts.py"
SPEC = importlib.util.spec_from_file_location("managed_artifacts", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ManagedArtifactsTest(unittest.TestCase):
    def test_manifest_drives_pruning_without_touching_unrelated_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            for path in (
                source / ".cursor/skills/keep",
                source / ".cursor/skills/new",
                source / ".cursor/agents",
                source / ".cursor/rules",
            ):
                path.mkdir(parents=True, exist_ok=True)
            (source / ".cursor/skills/keep/requirements.txt").write_text("")
            (source / ".cursor/agents/keep.md").write_text("")
            (source / ".cursor/rules/keep.mdc").write_text("")

            cursor, opencode, pi, pi_agents, mash = (
                root / "cursor",
                root / "opencode",
                root / "pi",
                root / "pi-agents",
                root / "mash",
            )
            for home in (cursor, opencode, pi):
                for name in ("old", "keep", "unrelated"):
                    (home / "skills" / name).mkdir(parents=True, exist_ok=True)
            for home in (cursor / "agents", opencode / "agents", pi_agents):
                home.mkdir(parents=True, exist_ok=True)
                for name in ("old.md", "keep.md", "unrelated.md"):
                    (home / name).write_text("")
            for name in ("old.mdc", "keep.mdc", "unrelated.mdc"):
                (cursor / "rules").mkdir(parents=True, exist_ok=True)
                (cursor / "rules" / name).write_text("")
            for kind in ("node_modules", "venvs"):
                for name in ("old", "keep", "unrelated"):
                    (mash / kind / name).mkdir(parents=True, exist_ok=True)

            manifest = mash / "install-manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                json.dumps(
                    {
                        "managed": {
                            "skills": ["keep", "old"],
                            "agents": ["keep.md", "old.md"],
                            "rules": ["keep.mdc", "old.mdc"],
                            "npm_skills": ["old"],
                            "venv_skills": ["keep", "old"],
                        }
                    }
                )
            )

            self.assertEqual(MODULE.names_for_uninstall(manifest, source, "skills"), ["keep", "old"])
            self.assertFalse(MODULE.manifest_matches(manifest, source))
            MODULE.prune(manifest, source, cursor, opencode, pi, pi_agents, mash)

            for home in (cursor, opencode, pi):
                self.assertFalse((home / "skills/old").exists())
                self.assertTrue((home / "skills/keep").exists())
                self.assertTrue((home / "skills/unrelated").exists())
            for home in (cursor / "agents", opencode / "agents", pi_agents):
                self.assertFalse((home / "old.md").exists())
                self.assertTrue((home / "unrelated.md").exists())
            self.assertFalse((cursor / "rules/old.mdc").exists())
            self.assertTrue((cursor / "rules/unrelated.mdc").exists())
            self.assertFalse((mash / "node_modules/old").exists())
            self.assertFalse((mash / "venvs/old").exists())
            self.assertTrue((mash / "venvs/keep").exists())
            self.assertTrue((mash / "venvs/unrelated").exists())

            MODULE.write_manifest(manifest, "1.2.3", source, cursor, opencode, pi, pi_agents, mash)
            written = json.loads(manifest.read_text())
            self.assertEqual(written["manifest_version"], 2)
            self.assertEqual(written["mash"], str(mash))
            self.assertEqual(written["managed"]["skills"], ["keep", "new"])
            self.assertEqual(MODULE.names_for_uninstall(manifest, source, "agents"), ["keep.md"])
            self.assertTrue(MODULE.manifest_matches(manifest, source))

    def _example(self, root, servers):
        path = root / "mcp.json.example"
        path.write_text(json.dumps({"mcpServers": servers}))
        return path

    def test_merge_keeps_unrelated_server_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            example = self._example(
                Path(tmp),
                {
                    "cua-driver": {"command": "cua-driver", "args": ["mcp"]},
                    "github": {"url": "https://example.invalid"},
                },
            )
            owned = MODULE.mcp_owned_names(example)
            existing = {
                "unrelated": {"command": "keep"},
                "cua-driver": {"command": "old"},
            }
            configured = {"cua-driver": {"command": "cua-driver", "args": ["mcp"]}}
            once = MODULE.merge_mcp_servers(existing, owned, configured)
            self.assertEqual(once["cua-driver"], configured["cua-driver"])
            self.assertEqual(once["unrelated"], {"command": "keep"})
            self.assertNotIn("github", once)
            self.assertEqual(MODULE.merge_mcp_servers(once, owned, configured), once)

    def test_empty_configured_map_removes_owned_names_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            example = self._example(
                Path(tmp),
                {"cua-driver": {"command": "cua-driver"}, "github": {"url": "https://example.invalid"}},
            )
            owned = MODULE.mcp_owned_names(example)
            existing = {"unrelated": {"command": "keep"}, "cua-driver": {"command": "old"}, "github": {"url": "x"}}
            result = MODULE.merge_mcp_servers(existing, owned, {})
            self.assertEqual(result, {"unrelated": {"command": "keep"}})

    def test_owned_names_do_not_invent_omitted_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            example = self._example(Path(tmp), {"context7": {"url": "https://example.invalid"}})
            self.assertEqual(MODULE.mcp_owned_names(example), {"context7"})

    def test_bad_mcp_example_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.json"
            with self.assertRaises(ValueError):
                MODULE.mcp_owned_names(missing)
            broken = root / "broken.json"
            broken.write_text("[]")
            with self.assertRaises(ValueError):
                MODULE.mcp_owned_names(broken)
            no_servers = root / "no-servers.json"
            no_servers.write_text("{}")
            with self.assertRaises(ValueError):
                MODULE.mcp_owned_names(no_servers)

    def test_shipped_example_registers_automation_servers(self):
        example = Path(__file__).parents[1] / ".cursor" / "mcp.json.example"
        servers = json.loads(example.read_text())["mcpServers"]
        browser_args = servers["agent-browser"]["args"]
        self.assertIn("core,network,debug", browser_args)
        devtools_args = " ".join(servers["chrome-devtools"]["args"])
        self.assertIn("chrome-devtools-mcp@1.10.1", devtools_args)
        self.assertIn("memoryDebugging", devtools_args)
        self.assertIn("isolated", devtools_args)
        self.assertNotIn("slim", devtools_args)
        self.assertNotIn("autoConnect", devtools_args)
        self.assertNotIn("auto-connect", devtools_args)
        self.assertEqual(servers["cua-driver"]["command"], "cua-driver")
        self.assertEqual(servers["cua-driver"]["args"], ["mcp"])

    def test_tool_pins_and_install_selection(self):
        self.assertEqual(
            MODULE.TOOL_PINS,
            {
                "cua-driver": "0.33.3",
                "agent-browser": "0.38.2",
                "chrome-devtools-mcp": "1.10.1",
            },
        )
        self.assertFalse(MODULE.binary_install_needed("cua-driver", "cua-driver 0.33.3"))
        self.assertTrue(MODULE.binary_install_needed("cua-driver", ""))
        self.assertTrue(MODULE.binary_install_needed("agent-browser", "agent-browser 0.1.0"))
        self.assertFalse(MODULE.binary_install_needed("chrome-devtools-mcp", ""))

    def test_installer_warns_and_skips_keepalive(self):
        text = (Path(__file__).parents[1] / "install.sh").read_text()
        self.assertIn("install_automation_tools || true", text)
        self.assertNotIn("KeepAlive", text)
        self.assertNotIn("--from=main", text)
        self.assertNotIn("permissions grant", text)
        self.assertIn("CuaDriver.app", text)


if __name__ == "__main__":
    unittest.main()
