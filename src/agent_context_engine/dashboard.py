"""Optional loopback dashboard. No execution endpoints; SDK works without this process."""
from dataclasses import asdict
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit
from .errors import EngineError, ValidationError
from .jsonutil import dumps, strict_loads
from .metrics import summarize
from .reports import export_csv, report_html
from .store import Access
from .telemetry import Telemetry, Scope, FILTERS


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, port: int, telemetry: Telemetry, access: Access, workspace: str, secret: str):
        if len(secret) < 16:
            raise ValidationError("Dashboard login secret must be at least 16 characters")
        access.require(workspace)
        self.telemetry, self.access, self.workspace, self.secret = telemetry, access, workspace, secret
        self.sessions: dict[str, float] = {}
        self.login_attempts: list[float] = []
        self.started = time.time()
        self.session_lock = threading.Lock()
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    server: DashboardServer
    def log_message(self, format: str, *args: Any) -> None:
        pass  # Never log login bodies, credentials, or URL parameters.

    def send(self, status: int, data: Any, kind: str = "application/json", cookie: str | None = None) -> None:
        raw = dumps(data).encode() if kind == "application/json" else data.encode() if isinstance(data, str) else data
        self.send_response(status)
        self.send_header("Content-Type", kind + ("; charset=utf-8" if kind.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(raw)

    def allowed_origin(self) -> bool:
        host = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != host:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin == "http://"+host

    def authenticated(self) -> bool:
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get("Cookie", ""))
        except Exception:
            return False
        value = cookies.get("ace_session")
        return bool(value and self.server.sessions.get(value.value, 0) > time.time())

    def scope(self) -> Scope:
        q = parse_qs(urlsplit(self.path).query)
        allowed = FILTERS | {"workspace", "mode", "start", "end", "search"}
        if q.keys() - allowed or any(len(v) != 1 for v in q.values()):
            raise ValidationError("Unknown/duplicate scope query")
        return Scope(q.get("workspace", [self.server.workspace])[0], q.get("mode", ["real"])[0],
            float(q["start"][0]) if q.get("start") else None, float(q["end"][0]) if q.get("end") else None,
            {k: q[k][0] for k in FILTERS if q.get(k)}, q.get("search", [""])[0])

    def do_GET(self) -> None:
        if not self.allowed_origin():
            self.send(403, {"error": "Host/origin denied"}); return
        path = urlsplit(self.path).path
        static = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
        if path in static:
            name, mime = static[path]
            self.send(200, (Path(__file__).parent/"web"/name).read_bytes(), mime); return
        if not self.authenticated():
            self.send(401, {"error": "Local session required"}); return
        try:
            scope = self.scope()
            events = self.server.telemetry.events(scope, self.server.access)
            settings = self.server.telemetry.settings(scope.workspace, self.server.access)
            if path == "/api/settings":
                self.send(200, settings); return
            if path == "/api/options":
                all_events = self.server.telemetry.events(Scope(scope.workspace, scope.mode), self.server.access)
                runs = [e["data"] for e in all_events if e["kind"] == "run"]
                self.send(200, {"default_workspace": self.server.workspace, "workspaces": sorted(self.server.access.workspaces), **{k: sorted({r[k] for r in runs if r.get(k)}) for k in FILTERS}}); return
            if path.startswith("/api/runs/"):
                rid = path.removeprefix("/api/runs/")
                own = [e for e in events if e["run_id"] == rid]
                self.send(200 if own else 404, {"events": own, "raw_content": "Unavailable: raw prompt/argument retention is not enabled for dashboard traces"}); return
            if path == "/api/health":
                import os
                rss: int | None
                cpu: float | None
                try:
                    import resource
                    r = resource.getrusage(resource.RUSAGE_SELF)
                    import platform
                    rss = r.ru_maxrss if platform.system() == "Darwin" else r.ru_maxrss * 1024
                    cpu = r.ru_utime+r.ru_stime
                except ImportError:
                    rss = cpu = None
                summary = summarize(events, scope, settings)
                self.send(200, {"scope": asdict(scope), "process_cpu_seconds": cpu, "process_peak_rss_bytes": rss, "process_scope": "Dashboard process including local analytics; agent process resource sampling is not installed",
                    "queue_depth": 0, "queue_reason": "Synchronous bounded SQLite writes; no background queue", "event_drops_since_start": self.server.telemetry.drops,
                    "errors_since_start": self.server.telemetry.errors, "database_bytes": self.server.telemetry.path.stat().st_size,
                    "active_runs": sum(r.get("end") is None for r in summary["runs"]), "engine_ms": summary["engine_ms"],
                    "telemetry_lag_ms": max((max(0, e["received"]-e["timestamp"])*1000 for e in events), default=None),
                    "events_in_scope": len(events), "events_per_second_since_dashboard_start": None,
                    "throughput_reason": "Historical ingestion rate not sampled", "original_store_bytes": None, "references_reason": "Each headless engine owns its reference store; not attached to this server"}); return
            summary = summarize(events, scope, settings)
            if path == "/api/summary" or path == "/api/export.json":
                self.send(200, summary)
            elif path == "/api/export.csv":
                self.send(200, export_csv(summary), "text/csv")
            elif path == "/api/report.html":
                self.send(200, report_html(summary), "text/html")
            else:
                self.send(404, {"error": "Endpoint not found"})
        except (EngineError, ValueError, TypeError) as exc:
            self.send(400 if isinstance(exc, ValidationError) else 403, {"error": str(exc)})

    def do_POST(self) -> None:
        if not self.allowed_origin() or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}":
            self.send(403, {"error": "Same-origin POST required"}); return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.send(415, {"error": "JSON required"}); return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 64_000:
                raise ValidationError("Request size limit")
            body = strict_loads(self.rfile.read(size).decode())
            path = urlsplit(self.path).path
            if path == "/api/login":
                with self.server.session_lock:
                    now = time.time()
                    self.server.login_attempts = [t for t in self.server.login_attempts if now-t < 60]
                    self.server.sessions = {k: v for k, v in self.server.sessions.items() if v > now}
                    if len(self.server.login_attempts) >= 10:
                        self.send(429, {"error": "Login rate limit; wait one minute"}); return
                    self.server.login_attempts.append(now)
                    if not isinstance(body, dict) or not isinstance(body.get("secret"), str) or not secrets.compare_digest(body["secret"], self.server.secret):
                        self.send(401, {"error": "Invalid local login secret"}); return
                    token = secrets.token_urlsafe(32)
                    self.server.sessions[token] = now+3600
                self.send(200, {"ok": True}, cookie=f"ace_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600")
            elif path == "/api/settings" and self.authenticated():
                scope = self.scope()
                value = self.server.telemetry.settings(scope.workspace, self.server.access, body)
                self.send(200, value)
            else:
                self.send(403, {"error": "Endpoint unavailable or unauthorized"})
        except (EngineError, ValueError, TypeError, KeyError) as exc:
            self.send(400, {"error": str(exc)})
