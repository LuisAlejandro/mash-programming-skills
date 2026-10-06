#!/usr/bin/env python3
"""Track and prune Mash Programming Skills-owned global artifacts."""

import argparse
import json
import shutil
from pathlib import Path

KINDS = ("skills", "agents", "rules", "npm_skills", "venv_skills")
TOOL_PINS = {
    "cua-driver": "0.33.3",
    "agent-browser": "0.38.2",
    "chrome-devtools-mcp": "1.10.1",
}
BINARY_TOOLS = frozenset({"cua-driver", "agent-browser"})


def inventory(source: Path):
    skills_dir = source / "src" / "skills"
    agents_dir = source / "src" / "agents"
    rules_dir = source / "src" / "rules"
    skills = sorted(path.name for path in skills_dir.iterdir() if path.is_dir()) if skills_dir.is_dir() else []
    return {
        "skills": skills,
        "agents": sorted(path.name for path in agents_dir.iterdir() if path.is_file()) if agents_dir.is_dir() else [],
        "rules": sorted(path.name for path in rules_dir.glob("*.mdc")) if rules_dir.is_dir() else [],
        "npm_skills": [name for name in skills if (skills_dir / name / "package.json").is_file()],
        "venv_skills": [name for name in skills if (skills_dir / name / "requirements.txt").is_file()],
    }


def load_managed(manifest: Path):
    try:
        managed = json.loads(manifest.read_text()).get("managed")
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(managed, dict):
        return None
    result = {}
    for kind in KINDS:
        names = managed.get(kind)
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            return None
        result[kind] = sorted({name for name in names if Path(name).name == name and name not in {"", ".", ".."}})
    return result


def remove(path: Path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        return False
    return True


def prune(manifest: Path, source: Path, cursor: Path, opencode: Path, pi: Path, pi_agents: Path, mash: Path):
    previous = load_managed(manifest)
    if previous is None:
        return
    current = inventory(source)
    targets = {
        "skills": (cursor / "skills", opencode / "skills", pi / "skills"),
        "agents": (cursor / "agents", opencode / "agents", pi_agents),
        "rules": (cursor / "rules",),
        "npm_skills": (mash / "node_modules",),
        "venv_skills": (mash / "venvs",),
    }
    for kind in KINDS:
        for name in sorted(set(previous[kind]) - set(current[kind])):
            removed = False
            for root in targets[kind]:
                removed = remove(root / name) or removed
            if removed:
                label = kind[:-7] if kind.endswith("_skills") else kind
                print(f"   pruned stale {label}: {name}")


def mcp_servers_for_manifest(example):
    if example is None or not Path(example).is_file():
        return []
    return sorted(mcp_owned_names(example))


def write_manifest(
    manifest: Path,
    version: str,
    source: Path,
    cursor: Path,
    opencode: Path,
    pi: Path,
    pi_agents: Path,
    mash: Path,
    mcp_example=None,
):
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": 2,
                "version": version,
                "source": str(source),
                "scope": "global",
                "cursor": str(cursor),
                "opencode": str(opencode),
                "pi": str(pi),
                "pi_agents": str(pi_agents),
                "mash": str(mash),
                "managed": inventory(source),
                "mcp_servers": mcp_servers_for_manifest(mcp_example),
            },
            indent=2,
        )
        + "\n"
    )


def binary_install_needed(name, reported):
    if name not in BINARY_TOOLS:
        return False
    return TOOL_PINS[name] not in str(reported or "").split()


def mcp_owned_names(example: Path):
    path = Path(example)
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"MCP example is unreadable: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("MCP example must be a JSON object")
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        raise ValueError("MCP example mcpServers must be an object")
    return set(servers)


def select_mcp_servers(servers, selected):
    if not isinstance(servers, dict):
        return {}
    if selected is None:
        return dict(servers)
    chosen = {name for name in selected if isinstance(name, str)}
    return {name: value for name, value in servers.items() if name in chosen}


def merge_mcp_servers(existing, owned, configured):
    if not isinstance(existing, dict):
        existing = {}
    if not isinstance(configured, dict):
        raise ValueError("configured servers must be an object")
    owned = set(owned)
    merged = {name: value for name, value in existing.items() if name not in owned}
    merged.update(configured)
    return merged


def names_for_uninstall(manifest: Path, source: Path, kind: str):
    managed = load_managed(manifest)
    return managed[kind] if managed is not None else inventory(source)[kind]


def manifest_matches(manifest: Path, source: Path):
    if load_managed(manifest) != inventory(source):
        return False
    try:
        servers = json.loads(manifest.read_text()).get("mcp_servers")
    except (OSError, json.JSONDecodeError, AttributeError):
        return False
    return isinstance(servers, list) and all(isinstance(name, str) for name in servers)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    prune_parser = commands.add_parser("prune")
    for name in ("manifest", "source", "cursor", "opencode", "pi", "pi_agents", "mash"):
        prune_parser.add_argument(name, type=Path)

    write_parser = commands.add_parser("write")
    write_parser.add_argument("manifest", type=Path)
    write_parser.add_argument("version")
    for name in ("source", "cursor", "opencode", "pi", "pi_agents", "mash"):
        write_parser.add_argument(name, type=Path)
    write_parser.add_argument("mcp_example", nargs="?", type=Path)

    list_parser = commands.add_parser("list")
    list_parser.add_argument("manifest", type=Path)
    list_parser.add_argument("source", type=Path)
    list_parser.add_argument("kind", choices=KINDS)

    check_parser = commands.add_parser("check")
    check_parser.add_argument("manifest", type=Path)
    check_parser.add_argument("source", type=Path)

    pin_parser = commands.add_parser("pin")
    pin_parser.add_argument("name", choices=sorted(TOOL_PINS))

    needed_parser = commands.add_parser("install-needed")
    needed_parser.add_argument("name")
    needed_parser.add_argument("reported", nargs="?", default="")

    args = parser.parse_args()
    if args.command == "prune":
        prune(args.manifest, args.source, args.cursor, args.opencode, args.pi, args.pi_agents, args.mash)
    elif args.command == "write":
        write_manifest(
            args.manifest,
            args.version,
            args.source,
            args.cursor,
            args.opencode,
            args.pi,
            args.pi_agents,
            args.mash,
            args.mcp_example,
        )
    elif args.command == "list":
        print("\n".join(names_for_uninstall(args.manifest, args.source, args.kind)))
    elif args.command == "pin":
        print(TOOL_PINS[args.name])
    elif args.command == "install-needed":
        print("yes" if binary_install_needed(args.name, args.reported) else "no")
    elif not manifest_matches(args.manifest, args.source):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
