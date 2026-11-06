"""HTTP checks for the mash-api-security probe.

The contract test guards the instructions. This file runs the skill script
against a local server so a status change fails here.
"""

import json
import os
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "src" / "skills" / "mash-api-security" / "scripts" / "run_api_checks.py"

SPEC = {
    "openapi": "3.0.3",
    "servers": [{"url": "https://prod.example.com"}],
    "paths": {
        "/health": {
            "get": {
                "operationId": "health",
                "security": [],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/login": {
            "post": {
                "operationId": "login",
                "security": [],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/notes/{id}": {
            "get": {
                "operationId": "getNote",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "note"}},
            }
        },
        "/notes": {
            "post": {
                "operationId": "createNote",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["body"],
                                "properties": {"body": {"type": "string"}},
                            }
                        }
                    },
                },
                "responses": {"201": {"description": "created"}},
            }
        },
    },
}


class ApiHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _send(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        origin = self.headers.get("Origin")
        if self.server.faulty and origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
        elif not self.server.faulty:
            self.send_header("Access-Control-Allow-Origin", "https://app.localhost")
        self.end_headers()
        self.wfile.write(data)

    def _bearer(self):
        header = self.headers.get("Authorization") or ""
        if header == "Bearer token-a":
            return "a"
        if header == "Bearer token-b":
            return "b"
        return ""

    def do_OPTIONS(self):
        self._send(204, "")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, '{"ok":true}')
            return
        if path.startswith("/notes/"):
            note_id = path.rsplit("/", 1)[-1]
            if not self.server.faulty:
                who = self._bearer()
                if not who:
                    self._send(401, '{"error":"unauthorized"}')
                    return
                if note_id != "user-a" and note_id != "user-b":
                    self._send(404, '{"error":"not found"}')
                    return
                if who == "b" and note_id == "user-a":
                    self._send(403, '{"error":"forbidden"}')
                    return
                self._send(200, json.dumps({"id": note_id, "owner": note_id, "body": "review"}))
                return
            if note_id == "does-not-exist":
                self._send(
                    500,
                    '{"error":"Traceback (most recent call last): File \\"app.py\\", line 1"}',
                )
                return
            self._send(200, '{"id":"user-a","owner":"user-a","body":"secret"}')
            return
        self._send(404, '{"error":"not found"}')

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b""
        path = self.path.split("?", 1)[0]
        if path == "/login":
            self.server.login_count += 1
            if not self.server.faulty and self.server.login_count > 5:
                self._send(429, '{"error":"slow down"}')
                return
            self._send(200, '{"ok":true}')
            return
        if path == "/notes":
            if raw == b"{":
                if self.server.faulty:
                    self._send(
                        500,
                        '{"error":"Traceback (most recent call last): File \\"app.py\\", line 2"}',
                    )
                else:
                    self._send(400, '{"error":"bad request"}')
                return
            if not self.server.faulty and not self._bearer():
                self._send(401, '{"error":"unauthorized"}')
                return
            try:
                sent = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                sent = {}
            if self.server.faulty:
                self._send(201, json.dumps({"id": "user-a", **sent}))
                return
            self._send(201, json.dumps({"id": "user-a", "body": sent.get("body", "")}))
            return
        self._send(404, '{"error":"not found"}')


def serve(faulty):
    server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
    server.faulty = faulty
    server.login_count = 0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def stop(server):
    server.shutdown()
    server.server_close()


def run_probe(base, spec_path):
    env = os.environ.copy()
    env.update(
        {
            "MASH_REVIEW_USER_A": "token-a",
            "MASH_REVIEW_USER_B": "token-b",
            "MASH_REVIEW_USER_A_ID": "user-a",
            "MASH_REVIEW_USER_B_ID": "user-b",
        }
    )
    completed = subprocess.run(
        ["python3", str(SCRIPT), "--spec", str(spec_path), "--base", base],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    return completed


def checks_from(completed):
    text = completed.stdout
    start = text.index("API_JSON") + len("API_JSON")
    end = text.index("END_API_JSON")
    document = json.loads(text[start:end])
    return {item["id"]: item for item in document["checks"]}


class ApiSecurityProbeTest(unittest.TestCase):
    def test_self_check(self):
        completed = subprocess.run(
            ["python3", str(SCRIPT), "--self-check"],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("self-check ok", completed.stdout)

    def test_production_host_is_refused_before_a_request(self):
        completed = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--spec",
                str(SCRIPT),
                "--base",
                "http://prod.example.com",
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertIn("no production target", completed.stderr)
        self.assertNotIn("API_JSON", completed.stdout)

    def test_faulty_and_clean_origins(self):
        spec_path = Path(os.environ.get("TMPDIR", "/tmp")) / "mash-api-security-spec.json"
        spec_path.write_text(json.dumps(SPEC))
        self.addCleanup(spec_path.unlink, missing_ok=True)
        faulty = serve(True)
        clean = serve(False)
        self.addCleanup(stop, faulty)
        self.addCleanup(stop, clean)
        faulty_checks = checks_from(
            run_probe(f"http://127.0.0.1:{faulty.server_address[1]}", spec_path)
        )
        clean_checks = checks_from(
            run_probe(f"http://127.0.0.1:{clean.server_address[1]}", spec_path)
        )

        self.assertEqual(faulty_checks["api.auth.get.notes.id"]["status"], "Fail")
        self.assertEqual(faulty_checks["api.auth.get.notes.id"]["severity"], "P0")
        self.assertEqual(clean_checks["api.auth.get.notes.id"]["status"], "Pass")
        self.assertEqual(faulty_checks["api.bola.get.notes.id"]["status"], "Fail")
        self.assertEqual(clean_checks["api.bola.get.notes.id"]["status"], "Pass")
        self.assertEqual(faulty_checks["api.mass-assignment"]["status"], "Fail")
        self.assertEqual(clean_checks["api.mass-assignment"]["status"], "Pass")
        self.assertEqual(faulty_checks["api.rate-limit"]["status"], "Fail")
        self.assertEqual(faulty_checks["api.rate-limit"]["severity"], "P2")
        self.assertEqual(clean_checks["api.rate-limit"]["status"], "Pass")
        self.assertEqual(faulty_checks["api.errors.verbose"]["status"], "Fail")
        self.assertEqual(clean_checks["api.errors.verbose"]["status"], "Pass")
        self.assertEqual(faulty_checks["api.cors"]["status"], "Fail")
        self.assertEqual(faulty_checks["api.cors"]["severity"], "P0")
        self.assertEqual(clean_checks["api.cors"]["status"], "Pass")
        self.assertEqual(faulty_checks["api.auth.get.health"]["status"], "Skipped")
        blob = json.dumps(faulty_checks)
        self.assertNotIn("token-a", blob)
        self.assertNotIn("token-b", blob)
        self.assertNotIn("https://prod.example.com", blob)


if __name__ == "__main__":
    unittest.main()
