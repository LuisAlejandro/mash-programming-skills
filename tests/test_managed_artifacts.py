import importlib.util
import json
import os
import subprocess
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
                source / "src/skills/keep",
                source / "src/skills/new",
                source / "src/agents",
                source / "src/rules",
            ):
                path.mkdir(parents=True, exist_ok=True)
            (source / "src/skills/keep/requirements.txt").write_text("")
            (source / "src/agents/keep.md").write_text("")
            (source / "src/rules/keep.mdc").write_text("")

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
            self.assertEqual(written["mcp_servers"], [])
            self.assertEqual(MODULE.names_for_uninstall(manifest, source, "agents"), ["keep.md"])
            self.assertTrue(MODULE.manifest_matches(manifest, source))
            written.pop("mcp_servers")
            manifest.write_text(json.dumps(written))
            self.assertFalse(MODULE.manifest_matches(manifest, source))

    def _example(self, root, servers):
        path = root / "mcp.json.example"
        path.write_text(json.dumps({"mcpServers": servers}))
        return path

    def test_selected_subset_is_what_gets_merged(self):
        servers = {
            "github": {"url": "x"},
            "context7": {"url": "y"},
            "sentrux": {"command": "sentrux"},
        }
        chosen = MODULE.select_mcp_servers(servers, ["context7"])
        self.assertEqual(set(chosen), {"context7"})
        self.assertEqual(MODULE.select_mcp_servers(servers, None), servers)
        self.assertEqual(MODULE.select_mcp_servers(servers, []), {})
        merged = MODULE.merge_mcp_servers(
            {"github": {"url": "old"}, "unrelated": {"command": "keep"}},
            set(servers),
            chosen,
        )
        self.assertEqual(set(merged), {"context7", "unrelated"})

    def test_installer_ignores_every_mash_working_directory(self):
        root = Path(__file__).parents[1]
        self.assertIn(".mash/", (root / ".gitignore").read_text().splitlines())
        installer = (root / "install.sh").read_text()
        self.assertIn("\n.mash/\n# End Mash Programming Skills", installer)
        self.assertNotIn(".mash/brainstorms/", installer)
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".gitignore").write_text(".mash/\n")
            self.assertEqual(
                subprocess.run(
                    ["git", "-C", str(repo), "check-ignore", "-q", ".mash/new-area/new-file.md"],
                    check=False,
                ).returncode,
                0,
            )

    def test_install_prompts_are_not_the_github_paste_alone(self):
        text = (Path(__file__).parents[1] / "install.sh").read_text()
        self.assertRegex(text, r"HINDSIGHT_LLM_PROVIDERS=\([^)]*\bnone\b")
        self.assertIn("select_mcp_servers", text)
        self.assertIn("Include github?", text)
        self.assertIn("MASH_INSTALL_SENTRUX", text)
        self.assertIn("MASH_INSTALL_CUA_DRIVER", text)
        self.assertIn("MASH_INSTALL_AGENT_BROWSER", text)
        self.assertNotIn("Paste a GitHub token, or press Enter to skip", text)

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
        install = (Path(__file__).parents[1] / "install.sh").read_text()
        catalog = install.split("cat <<'MASH_MCP_CATALOG'\n", 1)[1].split("\nMASH_MCP_CATALOG", 1)[0]
        servers = json.loads(catalog)["mcpServers"]
        self.assertIn('HINDSIGHT_PIN_VALUE="0.8.3"', install)
        self.assertIn("mash_hindsight_embed_template", install)
        root = Path(__file__).parents[1]
        self.assertFalse((root / "src/mcp.json.example").exists())
        self.assertFalse((root / "src/hindsight-pin").exists())
        self.assertFalse((root / "src/hindsight-embed.example").exists())
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

    def test_write_manifest_records_mcp_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            for path in (source / "src/skills", source / "src/agents", source / "src/rules"):
                path.mkdir(parents=True)
            example = self._example(source, {"github": {}, "context7": {}})
            manifest = root / "install-manifest.json"
            homes = [root / name for name in ("c", "o", "p", "a", "m")]
            MODULE.write_manifest(manifest, "1", source, *homes, example)
            self.assertEqual(json.loads(manifest.read_text())["mcp_servers"], ["context7", "github"])
            MODULE.write_manifest(manifest, "1", source, *homes, root / "missing.json")
            self.assertEqual(json.loads(manifest.read_text())["mcp_servers"], [])

    def _run_uninstall(self, home, *args):
        script = Path(__file__).parents[1] / "uninstall.sh"
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["GIT_CONFIG_GLOBAL"] = str(home / "gitconfig")
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        return subprocess.run(
            ["bash", str(script), *args],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_uninstall_uses_manifest_without_source_tree(self):
        script = (Path(__file__).parents[1] / "uninstall.sh").read_text()
        self.assertNotIn("managed_artifacts", script)
        self.assertNotIn("SOURCE_ROOT", script)
        self.assertNotIn("MASH_PROGRAMMING_SKILLS", script)
        install = (Path(__file__).parents[1] / "install.sh").read_text()
        self.assertIn('cp "$SOURCE_ROOT/uninstall.sh" "$MASH_CONFIG_DIR/uninstall.sh"', install)
        self.assertIn("mash_mcp_catalog_json", install)
        self.assertNotIn("src/mcp.json.example", install)
        self.assertNotIn("src/hindsight-pin", install)
        self.assertNotIn("src/hindsight-embed.example", install)

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            mash = home / ".config/mash"
            mash.mkdir(parents=True)
            cursor = home / ".cursor"
            opencode = home / ".config/opencode"
            for name in ("mash-work", "mine"):
                (cursor / "skills" / name).mkdir(parents=True)
                (opencode / "skills" / name).mkdir(parents=True)
            (cursor / "rules").mkdir(parents=True)
            (cursor / "rules/mash-workflow-gates.mdc").write_text("mash")
            (cursor / "rules/mine.mdc").write_text("mine")
            (cursor / "mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "github": {"url": "https://example.invalid"},
                            "penpot-local": {"command": "keep"},
                        }
                    }
                )
            )
            hook = home / ".cursor/hooks/ensure-hindsight-daemon.sh"
            hook.parent.mkdir(parents=True)
            hook.write_text("#!/bin/sh\n")
            (cursor / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "sessionStart": [
                                {"command": str(hook)},
                                {"command": "bash herdr"},
                            ]
                        }
                    }
                )
            )
            (mash / "AGENTS.md").write_text("Mash Programming Skills Agent Guidance\n")
            (mash / "uninstall.sh").write_text("sentinel")
            (mash / "install-manifest.json").write_text(
                json.dumps(
                    {
                        "version": "9.9.9",
                        "managed": {
                            "skills": ["mash-work"],
                            "agents": [],
                            "rules": ["mash-workflow-gates.mdc"],
                            "npm_skills": [],
                            "venv_skills": [],
                        },
                        "mcp_servers": ["github"],
                    }
                )
            )

            version = self._run_uninstall(home, "--version")
            self.assertEqual(version.returncode, 0)
            self.assertEqual(version.stdout.strip(), "9.9.9")

            dry = self._run_uninstall(home)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn("would remove", dry.stdout)
            self.assertTrue((cursor / "skills/mash-work").exists())

            applied = self._run_uninstall(home, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertFalse((cursor / "skills/mash-work").exists())
            self.assertTrue((cursor / "skills/mine").exists())
            self.assertFalse((opencode / "skills/mash-work").exists())
            self.assertTrue((opencode / "skills/mine").exists())
            self.assertFalse((cursor / "rules/mash-workflow-gates.mdc").exists())
            self.assertTrue((cursor / "rules/mine.mdc").exists())
            self.assertFalse(hook.exists())
            self.assertEqual(
                json.loads((cursor / "mcp.json").read_text())["mcpServers"],
                {"penpot-local": {"command": "keep"}},
            )
            hooks = json.loads((cursor / "hooks.json").read_text())
            self.assertEqual(
                [entry["command"] for entry in hooks["hooks"]["sessionStart"]],
                ["bash herdr"],
            )
            self.assertFalse(mash.exists())

    def test_uninstall_without_manifest_leaves_shared_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skill = home / ".cursor/skills/mash-work"
            skill.mkdir(parents=True)
            hook = home / ".cursor/hooks/ensure-hindsight-daemon.sh"
            hook.parent.mkdir(parents=True)
            hook.write_text("#!/bin/sh\n")
            (home / ".cursor/mcp.json").write_text(
                json.dumps({"mcpServers": {"github": {"url": "https://example.invalid"}}})
            )

            applied = self._run_uninstall(home, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("no install manifest", applied.stdout)
            self.assertTrue(skill.exists())
            self.assertFalse(hook.exists())
            self.assertIn("github", json.loads((home / ".cursor/mcp.json").read_text())["mcpServers"])

    def test_install_without_checkout_uses_master_tarball(self):
        repo = Path(__file__).parents[1]
        install = (repo / "install.sh").read_text()
        self.assertIn('MASH_GITHUB_REF="master"', install)
        self.assertIn("archive/refs/heads/${MASH_GITHUB_REF}.tar.gz", install)
        self.assertIn("api.github.com/repos/${MASH_GITHUB_REPO}/tarball/${MASH_GITHUB_REF}", install)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alone = root / "alone"
            alone.mkdir()
            script = alone / "install.sh"
            script.write_bytes((repo / "install.sh").read_bytes())
            script.chmod(0o755)
            bindir = root / "bin"
            bindir.mkdir()
            fake = bindir / "curl"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import sys, tarfile, tempfile\n"
                "from pathlib import Path\n"
                f"src = Path({str(script)!r})\n"
                "tree = Path(tempfile.mkdtemp()) / 'mash-programming-skills-master'\n"
                "(tree / 'src').mkdir(parents=True)\n"
                "(tree / 'VERSION').write_text('9.9.9\\n')\n"
                "(tree / 'install.sh').write_bytes(src.read_bytes())\n"
                "(tree / 'install.sh').chmod(0o755)\n"
                "with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as tar:\n"
                "    tar.add(tree, arcname='mash-programming-skills-master')\n"
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env.pop("MASH_PROGRAMMING_SKILLS", None)
            env.pop("MASH_INSTALL_TMP", None)
            env["HOME"] = str(root / "home")
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["GIT_CONFIG_GLOBAL"] = str(root / "gitconfig")
            env["GIT_CONFIG_NOSYSTEM"] = "1"
            result = subprocess.run(
                ["bash", str(script), "--version"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Downloading LuisAlejandro/mash-programming-skills@master", result.stdout)
            self.assertEqual(result.stdout.strip().splitlines()[-1], "9.9.9")

    def test_installer_warns_and_skips_keepalive(self):
        text = (Path(__file__).parents[1] / "install.sh").read_text()
        self.assertIn("install_automation_tools || true", text)
        self.assertNotIn("KeepAlive", text)
        self.assertNotIn("--from=main", text)
        self.assertNotIn("permissions grant", text)
        self.assertIn("CuaDriver.app", text)


if __name__ == "__main__":
    unittest.main()
