"""Loopback-only dashboard server; no wallet access or external requests."""

import argparse
import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from . import analyze
from .scenarios import run_scenarios, run_batch
from .store import RunStore

MAX_BODY = 1024 * 1024


def parse_payload(raw):
    def pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise ValueError("duplicate JSON key: " + key)
            output[key] = value
        return output

    def constant(value):
        raise ValueError("invalid JSON constant: " + value)

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError("payload must be an object")
    return value


def make_handler(store, token, example, title):
    assets = Path(__file__).parent / "web"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def respond(self, status, content, mime="application/json"):
            if mime == "application/json":
                content = json.dumps(content, allow_nan=False).encode()
            elif isinstance(content, str):
                content = content.encode()
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            )
            self.end_headers()
            self.wfile.write(content)

        def allowed_host(self):
            expected = "127.0.0.1:" + str(self.server.server_port)
            return self.headers.get("Host") == expected

        def authenticated(self):
            supplied = self.headers.get("X-Session-Token", "")
            return hmac.compare_digest(supplied, token)

        def do_GET(self):
            if not self.allowed_host():
                self.respond(403, {"error": "invalid host"})
                return
            url = urlsplit(self.path)
            if url.path in ("/", "/app.js", "/style.css"):
                name = {
                    "/": "index.html",
                    "/app.js": "app.js",
                    "/style.css": "style.css",
                }[url.path]
                mime = {
                    "index.html": "text/html",
                    "app.js": "application/javascript",
                    "style.css": "text/css",
                }[name]
                self.respond(200, (assets / name).read_bytes(), mime)
                return
            if url.path == "/api/bootstrap":
                # Same-origin browser access only; no CORS response headers.
                origin = self.headers.get("Origin")
                if origin and origin != "http://127.0.0.1:" + str(
                    self.server.server_port
                ):
                    self.respond(403, {"error": "invalid origin"})
                    return
                self.respond(200, {"token": token, "title": title, "example": example})
                return
            if not self.authenticated():
                self.respond(403, {"error": "session token required"})
                return
            try:
                if url.path == "/api/runs":
                    query = parse_qs(url.query)
                    before = int(query["before"][0]) if "before" in query else None
                    self.respond(200, store.list(before=before))
                elif url.path.startswith("/api/runs/"):
                    self.respond(200, store.get(int(url.path.split("/")[-1])))
                else:
                    self.respond(404, {"error": "route not found"})
            except KeyError as error:
                self.respond(404, {"error": str(error)})
            except ValueError as error:
                self.respond(400, {"error": str(error)})

        def do_POST(self):
            if not self.allowed_host() or not self.authenticated():
                self.respond(403, {"error": "valid host and session token required"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.respond(415, {"error": "application/json required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    self.respond(
                        413, {"error": "body must be between 1 byte and 1 MiB"}
                    )
                    return
                payload = parse_payload(self.rfile.read(length))
                route = urlsplit(self.path).path
                if route == "/api/analyze":
                    mode = "single"
                    output = analyze(payload["input"])
                elif route == "/api/scenarios":
                    mode = "scenario"
                    output = run_scenarios(payload["input"], payload["scenarios"])
                elif route == "/api/batch":
                    mode = "batch"
                    output = run_batch(payload["documents"])
                else:
                    self.respond(404, {"error": "route not found"})
                    return
                run_id = store.save(mode, payload.get("label", ""), payload, output)
                self.respond(200, {"run_id": run_id, "output": output})
            except (ValueError, KeyError, TypeError, ArithmeticError) as error:
                self.respond(400, {"error": str(error)})

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", default="runs.sqlite3")
    parser.add_argument("--example", default="examples/input.json")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("invalid port")
    example = parse_payload(Path(args.example).read_text())
    title = json.loads((Path(__file__).parent / "web" / "metadata.json").read_text())[
        "title"
    ]
    store = RunStore(args.db)
    server = HTTPServer(
        ("127.0.0.1", args.port),
        make_handler(store, secrets.token_hex(32), example, title),
    )
    server.timeout = 10
    print(f"{title}: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
