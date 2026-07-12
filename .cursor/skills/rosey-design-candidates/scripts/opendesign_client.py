"""OpenDesign CLI client for rosey-design-candidates (Discord-free port)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

PLUGIN_ID = "example-web-prototype"
SKIP_DISCOVERY_PREFIX = "skip questions, just build. no questions, go.\n\n"
OPENDESIGN_RUN_AGENT = "cursor-agent"
OPENDESIGN_RUN_POLL_INTERVAL_S = 5
OPENDESIGN_RUN_POLL_MAX_ATTEMPTS = 120
DEFAULT_DAEMON_URL = "http://127.0.0.1:7456"

OUTPUT_CONTRACT = """Output contract (hard requirements):
- Produce exactly one file named index.html in the project root.
- One polished screen only — not a multi-page site or screen gallery.
- Use the OpenDesign design system attached to this project; the DESIGN.md excerpt below is an additional guardrail.
- Use real, brief-specific copy. No lorem ipsum, filler sections, or placeholder stats.
- Self-contained HTML with inline CSS and minimal JS only.
"""


SKILL_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = SKILL_DIR / ".env"


def _load_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file (no quotes handling beyond strip)."""
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


class OpenDesignClient:
    def __init__(
        self,
        opendesign_bin: str = "opendesign",
        daemon_url: str = DEFAULT_DAEMON_URL,
        run_fn: Callable[..., str] | None = None,
    ) -> None:
        self.opendesign_bin = opendesign_bin
        self.daemon_url = daemon_url.rstrip("/")
        self._run_fn = run_fn
        self._subprocess_env = self._build_env()

    def _build_env(self) -> dict[str, str]:
        """Merge os.environ with skill .env file. .env values win."""
        env = dict(os.environ)
        dotenv = _load_dotenv(DOTENV_PATH)
        for key, value in dotenv.items():
            if value:  # skip empty values
                env[key] = value
        return env

    def preflight(self) -> tuple[bool, str]:
        import shutil

        resolved = shutil.which(self.opendesign_bin)
        bin_path = Path(self.opendesign_bin)
        if resolved:
            bin_path = Path(resolved)
        elif not bin_path.is_file():
            return False, f"opendesign_bin not found: {self.opendesign_bin}"
        if not os.access(bin_path, os.X_OK):
            return False, f"opendesign_bin not executable: {bin_path}"

        agents_url = f"{self.daemon_url}/api/agents"
        try:
            with urllib.request.urlopen(agents_url, timeout=5) as resp:
                if resp.status >= 400:
                    return False, f"OpenDesign daemon not reachable at {self.daemon_url}"
        except Exception as exc:
            return False, f"OpenDesign daemon not reachable at {self.daemon_url}: {exc}"

        return True, ""

    def run(self, *args: str) -> str:
        if self._run_fn is not None:
            return self._run_fn(*args)
        cmd = [self.opendesign_bin, *args]
        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, env=self._subprocess_env)
        if result.returncode != 0:
            logger.error("opendesign stderr: %s", result.stderr)
            raise RuntimeError(f"opendesign failed: {result.stderr}")
        return result.stdout

    def create_project(
        self,
        name: str,
        *,
        design_system_id: str,
        metadata_json_path: Path | None = None,
    ) -> dict[str, Any]:
        args = [
            "project",
            "create",
            "--name",
            name,
            "--plugin",
            PLUGIN_ID,
            "--design-system",
            design_system_id,
            "--json",
        ]
        if metadata_json_path is not None:
            args.extend(["--metadata-json", str(metadata_json_path)])
        out = self.run(*args)
        data = json.loads(out)
        project = data.get("project") or {}
        project_id = project.get("id") or data.get("projectId")
        conversation_id = data.get("conversationId")
        if not conversation_id and isinstance(data.get("conversation"), dict):
            conversation_id = data["conversation"].get("id")
        if not project_id:
            raise RuntimeError(f"project create missing project id: {data}")
        return {"project_id": project_id, "conversation_id": conversation_id}

    def run_until_complete(
        self,
        project_id: str,
        message: str,
        *,
        conversation_id: str | None = None,
        model: str | None = None,
        poll_interval_s: float = OPENDESIGN_RUN_POLL_INTERVAL_S,
        max_attempts: int = OPENDESIGN_RUN_POLL_MAX_ATTEMPTS,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> str:
        sleep = sleep_fn or time.sleep
        run_message = SKIP_DISCOVERY_PREFIX + message.strip()
        run_args = [
            "run",
            "start",
            "--project",
            project_id,
            "--message",
            run_message,
            "--agent",
            OPENDESIGN_RUN_AGENT,
            "--json",
        ]
        if conversation_id:
            run_args.extend(["--conversation", conversation_id])
        if model:
            run_args.extend(["--model", model])

        out = self.run(*run_args)
        data = json.loads(out)
        run_id = data.get("runId", "")
        if not run_id:
            raise RuntimeError(f"run start missing runId: {data}")

        state = ""
        for attempt in range(max_attempts):
            sleep(poll_interval_s)
            try:
                status_out = self.run("run", "info", run_id, "--json")
                status = json.loads(status_out)
                state = status.get("status", "")
                if state in ("complete", "completed", "succeeded"):
                    return run_id
                if state in ("failed", "cancelled"):
                    error_msg = status.get("error", "")
                    error_code = status.get("errorCode", "")
                    raise RuntimeError(
                        f"Run {run_id} failed with state: {state}"
                        f" (errorCode={error_code}, error={error_msg})"
                    )
            except RuntimeError:
                raise
            except Exception as exc:
                if attempt % 6 == 0:
                    logger.warning("Poll error: %s", exc)

        raise RuntimeError(
            f"Run {run_id} timed out after {max_attempts * poll_interval_s}s "
            f"(last status: {state or 'unknown'})"
        )

    def export_html(self, project_id: str, dest: Path) -> None:
        files_out = self.run("files", "list", project_id, "--json")
        data = json.loads(files_out)
        files = data.get("files", [])
        entry = None
        for f in files:
            if f.get("name") == "index.html" or f.get("kind") == "html":
                entry = f.get("name")
                break
        if not entry:
            for f in files:
                if str(f.get("name", "")).endswith(".html"):
                    entry = f.get("name")
                    break
        if not entry:
            raise RuntimeError(f"No HTML artifact found in project {project_id}")
        html_out = self.run("files", "read", project_id, entry)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_out, encoding="utf-8")

    def delete_project(self, project_id: str) -> None:
        try:
            self.run("project", "delete", "--project", project_id, "--json")
        except Exception as exc:
            logger.warning("Failed to delete project %s: %s", project_id, exc)


def parse_create_response(stdout: str) -> dict[str, Any]:
    """Test helper: parse project create JSON."""
    data = json.loads(stdout)
    project = data.get("project") or {}
    project_id = project.get("id") or data.get("projectId")
    conversation_id = data.get("conversationId")
    if not conversation_id and isinstance(data.get("conversation"), dict):
        conversation_id = data["conversation"].get("id")
    return {"project_id": project_id, "conversation_id": conversation_id, "raw": data}


def parse_run_start_response(stdout: str) -> str:
    data = json.loads(stdout)
    run_id = data.get("runId", "")
    if not run_id:
        raise RuntimeError(f"run start missing runId: {data}")
    return run_id
