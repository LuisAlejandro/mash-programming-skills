#!/usr/bin/env python3
"""Probe one local or staging origin from an OpenAPI document.

Skill tooling for mash-api-security. Not the app under review.

ponytail: path parameters are filled from the two account ids only. A path
with several different ids needs a later map. The rate burst is sequential,
so a limit that trips only under concurrency is outside this check.
"""

import argparse
import http.client
import ipaddress
import json
import os
import re
import shlex
import sys
import urllib.parse
from pathlib import Path

BURST = 20
PRIVILEGED_TEMPLATE = (
    ("role", "admin"),
    ("isAdmin", True),
    ("is_admin", True),
    ("admin", True),
    ("ownerId", None),
)
OWNER_KEYS = ("owner", "ownerId", "userId", "user_id", "accountId")
STAGING_LABELS = {
    "staging",
    "stage",
    "stg",
    "dev",
    "preview",
    "qa",
    "test",
    "sandbox",
    "uat",
    "local",
}
PROD_LABELS = {"prod", "production"}
METHODS = ("get", "post", "put", "patch", "delete")
VERBOSE = re.compile(
    r"Traceback \(most recent call last\)|"
    r"\bat [\w./\\]+\([^)\n]*:\d+:\d+\)|"
    r"SQLSTATE|psycopg2|sqlite3\.OperationalError|syntax error at or near|"
    r"/home/|/var/|/usr/",
    re.IGNORECASE,
)


def classify_host(host):
    host = (host or "").lower().strip("[]").rstrip(".")
    labels = host.split(".")
    if any(label in PROD_LABELS for label in labels):
        return "refuse"
    if host in {
        "localhost",
        "127.0.0.1",
        "::1",
        "host.docker.internal",
    } or host.endswith(".localhost") or host.endswith(".local"):
        return "local"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        return "local" if address.is_loopback else "refuse"
    if any(label in STAGING_LABELS for label in labels):
        return "staging"
    return "refuse"


def requirement(spec, operation):
    if "security" in operation:
        security = operation["security"]
    elif "security" in spec:
        security = spec["security"]
    else:
        return "unspecified"
    if not security:
        return "public"
    return "required"


def check_id(prefix, method, path):
    slug = path.strip("/").replace("/", ".").replace("{", "").replace("}", "")
    slug = re.sub(r"[^A-Za-z0-9.]+", ".", slug).strip(".") or "root"
    return f"{prefix}.{method.lower()}.{slug}"


def redact(text, secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    text = re.sub(
        r"(?i)(authorization:\s*bearer\s+)\S+",
        r"\1[redacted]",
        text,
    )
    text = re.sub(
        r"(?i)(\"(?:password|token|access_token|refresh_token|secret|api_key|apikey)\"\s*:\s*\")[^\"]*",
        r"\1[redacted]",
        text,
    )
    return text


def privileged_values(other_id):
    values = {}
    for key, value in PRIVILEGED_TEMPLATE:
        values[key] = other_id if key == "ownerId" else value
    return values


def injectable_fields(schema, other_id):
    props = (schema or {}).get("properties") or {}
    injected = {}
    for key, value in privileged_values(other_id).items():
        prop = props.get(key)
        if prop is None or prop.get("readOnly") is True:
            injected[key] = value
    return injected


def privileged_hit(payload, injected):
    if not isinstance(payload, dict):
        return False
    for key, value in injected.items():
        if key in payload and payload[key] == value:
            return True
    return False


def json_object(schema):
    schema = schema or {}
    body = {}
    props = schema.get("properties") or {}
    for name in schema.get("required") or []:
        kind = (props.get(name) or {}).get("type")
        if kind in ("integer", "number"):
            body[name] = 1
        elif kind == "boolean":
            body[name] = False
        else:
            body[name] = "review"
    return body


def request_schema(operation):
    content = ((operation.get("requestBody") or {}).get("content") or {})
    media = content.get("application/json") or {}
    return media.get("schema") or {}


def fill_path(path, value):
    return re.sub(
        r"\{[^}]+\}",
        urllib.parse.quote(str(value), safe=""),
        path,
    )


def join_url(base, path):
    return base.rstrip("/") + "/" + path.lstrip("/")


def operations(spec):
    found = []
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in METHODS:
            operation = item.get(method)
            if isinstance(operation, dict):
                found.append((method, path, operation))
    return found


def curl_command(method, url, headers, body):
    parts = ["curl", "-sS", "-D", "-", "-o", "-", "-X", method.upper(), shlex.quote(url)]
    for key, value in headers.items():
        parts.extend(["-H", shlex.quote(f"{key}: {value}")])
    if body is not None:
        parts.extend(["--data-binary", shlex.quote(body.decode())])
    return " ".join(parts)


def exchange(method, url, headers, body=None, timeout=5):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"unsupported URL {url}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if parsed.scheme == "https":
        connection = http.client.HTTPSConnection(parsed.hostname, port, timeout=timeout)
    else:
        connection = http.client.HTTPConnection(parsed.hostname, port, timeout=timeout)
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query
    try:
        connection.request(method.upper(), target, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read(8192)
        status = response.status
        header_map = {key.lower(): value for key, value in response.getheaders()}
    finally:
        connection.close()
    return status, header_map, payload


def row(check, title, status, severity, hint, command, output, detail):
    return {
        "id": check,
        "title": title,
        "status": status,
        "severity": severity,
        "hint": hint,
        "command": command,
        "output": output,
        "detail": detail,
    }


def preview(status, headers, payload, secrets):
    text = payload.decode("utf-8", "replace")
    header_text = "\n".join(f"{key}: {value}" for key, value in headers.items())
    shown = f"HTTP {status}\n{header_text}\n{text}"
    shown = redact(shown, secrets)
    if len(shown) > 800:
        shown = shown[:800] + "\n[truncated]"
    return shown


def auth_header(token):
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def owner_is_other(payload, other_id, caller_id):
    if not other_id or other_id == caller_id:
        return False
    try:
        data = json.loads(payload.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    for key in OWNER_KEYS:
        if str(data.get(key)) == str(other_id):
            return True
    return str(data.get("id")) == str(other_id)


def load_spec(path):
    text = Path(path).read_text()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError:
            raise SystemExit(
                "Blocked: PyYAML is not installed. Convert the spec to JSON."
            )
        spec = yaml.safe_load(text)
    else:
        spec = json.loads(text)
    if not isinstance(spec, dict) or not isinstance(spec.get("paths"), dict):
        raise SystemExit("spec has no paths object")
    return spec


def probe(spec, base, accounts, secrets):
    checks = []
    token_a = accounts.get("a") or ""
    token_b = accounts.get("b") or ""
    id_a = accounts.get("a_id") or "sample"
    id_b = accounts.get("b_id") or ""
    ops = operations(spec)

    for method, path, operation in ops:
        url = join_url(base, fill_path(path, id_a))
        headers = {"Accept": "application/json"}
        command = curl_command(method, url, headers, None)
        ident = check_id("api.auth", method, path)
        title = f"Authentication on {method.upper()} {path}"
        level = requirement(spec, operation)
        if level == "public":
            checks.append(
                row(
                    ident,
                    title,
                    "Skipped",
                    "",
                    "",
                    command,
                    "",
                    "spec marks security as empty",
                )
            )
            continue
        try:
            status, headers_out, payload = exchange(method, url, headers)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            checks.append(
                row(
                    ident,
                    title,
                    "Blocked (needs human verify)",
                    "",
                    "",
                    command,
                    redact(str(exc), secrets),
                    "request did not complete",
                )
            )
            continue
        output = preview(status, headers_out, payload, secrets)
        if status in (401, 403):
            state, severity, detail = "Pass", "", f"HTTP {status} without credentials"
        elif 200 <= status < 300:
            state, severity, detail = (
                "Fail",
                "P0",
                f"HTTP {status} without credentials",
            )
        else:
            state, severity, detail = (
                "Blocked (needs human verify)",
                "",
                f"HTTP {status} was not 401, 403, or a 2xx body",
            )
        hint = "OWASP API Security API2 Broken Authentication" if state == "Fail" else ""
        checks.append(row(ident, title, state, severity, hint, command, output, detail))

    bola_ready = bool(token_b and accounts.get("a_id") and accounts.get("b_id"))
    for method, path, operation in ops:
        if "{" not in path:
            continue
        ident = check_id("api.bola", method, path)
        title = f"Object access on {method.upper()} {path}"
        url = join_url(base, fill_path(path, accounts.get("a_id") or "sample"))
        headers = {"Accept": "application/json"}
        headers.update(auth_header(token_b))
        command = redact(curl_command(method, url, headers, None), secrets)
        if not bola_ready:
            checks.append(
                row(
                    ident,
                    title,
                    "Blocked (needs human verify)",
                    "",
                    "",
                    command,
                    "",
                    "set MASH_REVIEW_USER_B, MASH_REVIEW_USER_A_ID, and MASH_REVIEW_USER_B_ID",
                )
            )
            continue
        try:
            status, headers_out, payload = exchange(method, url, headers)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            checks.append(
                row(
                    ident,
                    title,
                    "Blocked (needs human verify)",
                    "",
                    "",
                    command,
                    redact(str(exc), secrets),
                    "request did not complete",
                )
            )
            continue
        output = preview(status, headers_out, payload, secrets)
        if status in (401, 403, 404):
            checks.append(
                row(ident, title, "Pass", "", "", command, output, f"HTTP {status}")
            )
        elif 200 <= status < 300 and owner_is_other(payload, accounts.get("a_id"), accounts.get("b_id")):
            checks.append(
                row(
                    ident,
                    title,
                    "Fail",
                    "P0",
                    "OWASP API Security API1 Broken Object Level Authorization",
                    command,
                    output,
                    "user B received user A's object",
                )
            )
        elif 200 <= status < 300:
            checks.append(
                row(
                    ident,
                    title,
                    "Blocked (needs human verify)",
                    "",
                    "",
                    command,
                    output,
                    "HTTP 2xx but ownership was not in the body",
                )
            )
        else:
            checks.append(
                row(
                    ident,
                    title,
                    "Blocked (needs human verify)",
                    "",
                    "",
                    command,
                    output,
                    f"HTTP {status} was not 401, 403, 404, or a 2xx body",
                )
            )

    checks.append(mass_assignment(spec, base, token_a, id_b or "review-owner", secrets))
    checks.append(rate_limit(spec, base, secrets))
    checks.append(verbose_errors(spec, base, secrets))
    checks.append(cors_check(spec, base, secrets))
    return checks


def write_target(spec):
    for method, path, operation in operations(spec):
        if method in ("post", "put", "patch") and "login" not in path and "login" not in str(operation.get("operationId") or ""):
            return method, path, operation
    return None


def rate_target(spec):
    for method, path, operation in operations(spec):
        label = path + " " + str(operation.get("operationId") or "")
        if any(piece in label.lower() for piece in ("login", "signin", "token")):
            return method, path
    found = operations(spec)
    if not found:
        return None
    return found[0][0], found[0][1]


def mass_assignment(spec, base, token_a, other_id, secrets):
    ident = "api.mass-assignment"
    title = "Privileged fields on a write"
    target = write_target(spec)
    if target is None:
        return row(ident, title, "Skipped", "", "", "", "", "no write operation")
    if not token_a:
        return row(
            ident,
            title,
            "Blocked (needs human verify)",
            "",
            "",
            "",
            "",
            "set MASH_REVIEW_USER_A",
        )
    method, path, operation = target
    schema = request_schema(operation)
    injected = injectable_fields(schema, other_id)
    if schema.get("properties") and not injected:
        return row(
            ident,
            title,
            "Skipped",
            "",
            "",
            "",
            "",
            "spec marks the privileged names as writable",
        )
    if not injected:
        injected = privileged_values(other_id)
    body_obj = json_object(schema)
    body_obj.update(injected)
    raw = json.dumps(body_obj).encode()
    url = join_url(base, fill_path(path, "sample"))
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    headers.update(auth_header(token_a))
    command = redact(curl_command(method, url, headers, raw), secrets)
    try:
        status, headers_out, payload = exchange(method, url, headers, raw)
    except (OSError, http.client.HTTPException, ValueError) as exc:
        return row(
            ident,
            title,
            "Blocked (needs human verify)",
            "",
            "",
            command,
            redact(str(exc), secrets),
            "request did not complete",
        )
    bodies = [payload]
    try:
        created = json.loads(payload.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        created = None
    if isinstance(created, dict) and created.get("id"):
        follow = follow_get(spec, base, path, created["id"], token_a)
        if follow is not None:
            bodies.append(follow[2])
            payload = payload + b"\n" + follow[2]
            headers_out = follow[1]
            status = follow[0]
    output = preview(status, headers_out, payload, secrets)
    hit = any(privileged_hit(parse_json(body), injected) for body in bodies)
    if hit:
        return row(
            ident,
            title,
            "Fail",
            "P0",
            "OWASP API Security API3 Broken Object Property Level Authorization",
            command,
            output,
            "a privileged field was returned with the injected value",
        )
    return row(
        ident,
        title,
        "Pass",
        "",
        "",
        command,
        output,
        "the write did not return the injected privileged fields",
    )


def parse_json(payload):
    try:
        return json.loads(payload.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return None


def follow_get(spec, base, write_path, created_id, token):
    prefix = write_path.rstrip("/")
    for method, path, _operation in operations(spec):
        if method != "get" or "{" not in path:
            continue
        if path.split("{", 1)[0].rstrip("/") == prefix:
            url = join_url(base, fill_path(path, created_id))
            headers = {"Accept": "application/json"}
            headers.update(auth_header(token))
            try:
                return exchange("GET", url, headers)
            except (OSError, http.client.HTTPException, ValueError):
                return None
    return None


def rate_limit(spec, base, secrets):
    ident = "api.rate-limit"
    title = "Rate limit on a repeated request"
    target = rate_target(spec)
    if target is None:
        return row(ident, title, "Skipped", "", "", "", "", "spec has no operations")
    method, path = target
    url = join_url(base, fill_path(path, "sample"))
    raw = b"{}"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    command = curl_command(method, url, headers, raw) + f"  # repeated {BURST} times"
    seen = []
    last = None
    try:
        for _ in range(BURST):
            status, headers_out, payload = exchange(method, url, headers, raw)
            seen.append(status)
            last = (status, headers_out, payload)
    except (OSError, http.client.HTTPException, ValueError) as exc:
        return row(
            ident,
            title,
            "Blocked (needs human verify)",
            "",
            "",
            command,
            redact(str(exc), secrets),
            "request did not complete",
        )
    output = preview(last[0], last[1], last[2], secrets)
    output = f"statuses={seen}\n" + output
    if 429 in seen:
        return row(ident, title, "Pass", "", "", command, output, "at least one HTTP 429")
    return row(
        ident,
        title,
        "Fail",
        "P2",
        "OWASP API Security API4 Unrestricted Resource Consumption",
        command,
        output,
        f"no HTTP 429 in {BURST} sequential requests",
    )


def verbose_errors(spec, base, secrets):
    ident = "api.errors.verbose"
    title = "Error body stays generic"
    target = write_target(spec) or (operations(spec)[0] if operations(spec) else None)
    if target is None:
        return row(ident, title, "Skipped", "", "", "", "", "spec has no operations")
    method, path, _operation = target
    url = join_url(base, fill_path(path, "does-not-exist"))
    raw = b"{"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    command = curl_command(method, url, headers, raw)
    chunks = []
    try:
        status, headers_out, payload = exchange(method, url, headers, raw)
        chunks.append(preview(status, headers_out, payload, secrets))
        get_path = None
        for get_method, candidate, _operation in operations(spec):
            if get_method == "get" and "{" in candidate:
                get_path = candidate
                break
        if get_path:
            get_url = join_url(base, fill_path(get_path, "does-not-exist"))
            status, headers_out, payload = exchange("GET", get_url, {"Accept": "application/json"})
            chunks.append(preview(status, headers_out, payload, secrets))
    except (OSError, http.client.HTTPException, ValueError) as exc:
        return row(
            ident,
            title,
            "Blocked (needs human verify)",
            "",
            "",
            command,
            redact(str(exc), secrets),
            "request did not complete",
        )
    output = "\n---\n".join(chunks)
    if VERBOSE.search(output):
        return row(
            ident,
            title,
            "Fail",
            "P1",
            "OWASP Top 10 A05 Security Misconfiguration",
            command,
            output,
            "the error body included a stack, a SQL driver error, or a filesystem path",
        )
    return row(ident, title, "Pass", "", "", command, output, "error bodies stayed generic")


def cors_check(spec, base, secrets):
    ident = "api.cors"
    title = "Foreign Origin is not allowed"
    found = operations(spec)
    path = "/"
    for method, candidate, _operation in found:
        if method == "get":
            path = candidate
            break
    url = join_url(base, fill_path(path, "sample"))
    headers = {
        "Origin": "https://evil.example",
        "Access-Control-Request-Method": "GET",
        "Accept": "application/json",
    }
    command = curl_command("OPTIONS", url, headers, None)
    try:
        status, headers_out, payload = exchange("OPTIONS", url, headers)
        get_status, get_headers, get_payload = exchange(
            "GET",
            url,
            {"Origin": "https://evil.example", "Accept": "application/json"},
        )
    except (OSError, http.client.HTTPException, ValueError) as exc:
        return row(
            ident,
            title,
            "Blocked (needs human verify)",
            "",
            "",
            command,
            redact(str(exc), secrets),
            "request did not complete",
        )
    output = preview(status, headers_out, payload, secrets) + "\n---\n" + preview(
        get_status, get_headers, get_payload, secrets
    )
    allow = (headers_out.get("access-control-allow-origin") or get_headers.get("access-control-allow-origin") or "")
    credentials = (
        headers_out.get("access-control-allow-credentials")
        or get_headers.get("access-control-allow-credentials")
        or ""
    ).lower() == "true"
    reflected = allow == "https://evil.example"
    if reflected and credentials:
        state, severity = "Fail", "P0"
        detail = "the foreign Origin was reflected and credentials were allowed"
    elif allow == "*" or reflected:
        state, severity = "Fail", "P1"
        detail = f"Access-Control-Allow-Origin was {allow}"
    else:
        state, severity = "Pass", ""
        detail = "the foreign Origin was not allowed"
    hint = "OWASP Top 10 A05 Security Misconfiguration" if state == "Fail" else ""
    return row(ident, title, state, severity, hint, command, output, detail)


def emit(checks, base, spec_path):
    document = {"base": base, "spec": spec_path, "checks": checks}
    encoded = json.dumps(document, indent=2)
    print("API_JSON")
    print(encoded)
    print("END_API_JSON")
    return document


def self_check():
    spec = {
        "paths": {
            "/health": {"get": {"security": []}},
            "/notes/{id}": {"get": {"security": [{"bearerAuth": []}]}},
        }
    }
    bare = {"paths": {"/x": {"get": {}}}}
    assert requirement(spec, spec["paths"]["/health"]["get"]) == "public"
    assert requirement(spec, spec["paths"]["/notes/{id}"]["get"]) == "required"
    assert requirement(bare, bare["paths"]["/x"]["get"]) == "unspecified"
    assert classify_host("127.0.0.1") == "local"
    assert classify_host("::1") == "local"
    assert classify_host("prod.example.com") == "refuse"
    assert classify_host("production.localhost") == "refuse"
    assert classify_host("api.staging.example.com") == "staging"
    assert classify_host("example.com") == "refuse"
    assert classify_host("10.1.1.1") == "refuse"
    assert redact("Bearer secret-token", ["secret-token"]) == "Bearer [redacted]"
    injected = {"isAdmin": True, "role": "admin"}
    assert privileged_hit({"isAdmin": True, "body": "review"}, injected)
    assert not privileged_hit({"body": "review"}, injected)
    schema = {"properties": {"role": {"type": "string"}, "body": {"type": "string"}}}
    assert "role" not in injectable_fields(schema, "user-b")
    assert "isAdmin" in injectable_fields(schema, "user-b")
    print("self-check ok")
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Probe an OpenAPI origin")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--spec")
    parser.add_argument("--base")
    parser.add_argument("--out")
    parser.add_argument("--allow-staging", action="store_true")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    if args.self_check:
        return self_check()
    if not args.spec or not args.base:
        print("usage: run_api_checks.py --spec <file> --base <origin>", file=sys.stderr)
        return 1
    parsed = urllib.parse.urlsplit(args.base)
    kind = classify_host(parsed.hostname)
    if kind == "refuse":
        print("refused: this kit has no production target", file=sys.stderr)
        return 3
    if kind == "staging" and not args.allow_staging:
        print("refused: staging requires --allow-staging", file=sys.stderr)
        return 3
    try:
        spec = load_spec(args.spec)
    except (OSError, json.JSONDecodeError, SystemExit) as exc:
        message = exc.code if isinstance(exc, SystemExit) else exc
        print(message, file=sys.stderr)
        return 1
    accounts = {
        "a": os.environ.get("MASH_REVIEW_USER_A", ""),
        "b": os.environ.get("MASH_REVIEW_USER_B", ""),
        "a_id": os.environ.get("MASH_REVIEW_USER_A_ID", ""),
        "b_id": os.environ.get("MASH_REVIEW_USER_B_ID", ""),
    }
    secrets = [accounts["a"], accounts["b"]]
    checks = probe(spec, args.base, accounts, secrets)
    finished = row(
        "api.probe",
        "OpenAPI probe finished",
        "Pass",
        "",
        "",
        "python3 scripts/run_api_checks.py --spec "
        + shlex.quote(args.spec)
        + " --base "
        + shlex.quote(args.base),
        f"probes finished: {len(checks)} checks",
        "the script finished",
    )
    document = emit([finished] + checks, args.base, args.spec)
    if args.out:
        Path(args.out).write_text(json.dumps(document, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
