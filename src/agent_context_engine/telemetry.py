"""Bounded metadata-only SQLite ingestion. No raw prompts, arguments, or reasoning."""
from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any
from uuid import uuid4
from .errors import ValidationError
from .jsonutil import dumps, strict_loads
from .store import Access

COMMON = {"trace_id", "span_id", "parent_span_id", "task_id", "engine_version", "config_version"}
ALLOWED = {
    "run": {"task", "agent", "provider", "model", "tokenizer", "benchmark", "arm", "pair_id", "config", "method", "start", "end", "success", "validator", "evidence", "expected_requests", "failure_code", "price_version"},
    "usage": {"provider", "model", "input_tokens", "output_tokens", "cached_input_tokens", "cache_write_tokens", "reasoning_tokens", "tool_cost", "raw_usage", "final", "purpose", "evidence", "price_version", "provider_wait_ms"},
    "optimization": {"method", "original_tokens", "optimized_tokens", "tokenizer", "duration_ms", "bypass_reason", "evidence"},
    "command": {"operation", "schema_version", "registry_version", "valid", "executed", "exit_code", "duration_ms", "compact_tokens", "native_tokens", "arguments", "invocation", "request_digest"},
    "retrieval": {"valid", "duration_ms"}, "retry": {"reason_code"},
    "check": {"validator", "category", "valid", "failure_code", "evidence"},
}
FILTERS = {"agent", "provider", "model", "engine_version", "method", "benchmark", "tokenizer", "arm"}


@dataclass(frozen=True)
class Scope:
    workspace: str
    mode: str = "real"
    start: float | None = None
    end: float | None = None
    filters: dict[str, str] = field(default_factory=dict)
    search: str = ""

    def __post_init__(self) -> None:
        if self.mode not in {"real", "demo"} or self.filters.keys() - FILTERS:
            raise ValidationError("Invalid telemetry scope")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValidationError("Invalid date range")


def sanitize(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    if kind not in ALLOWED or not isinstance(data, dict) or data.keys() - ALLOWED[kind] - COMMON:
        raise ValidationError("Unknown telemetry fields; raw content is not accepted")
    clean = dict(data)
    for key in ("arguments", "invocation"):
        if key in clean:
            clean[key] = "[redacted; use authorized local dry-run]"
    for key, value in clean.items():
        if key.endswith("tokens") or key in {"expected_requests"}:
            if value is not None and (type(value) is not int or value < 0):
                raise ValidationError("Usage counts must be nonnegative integers or null")
        elif key in {"success", "valid", "final", "executed"}:
            if value is not None and type(value) is not bool:
                raise ValidationError("Invalid boolean metric")
        elif key in {"duration_ms", "provider_wait_ms", "start", "end", "tool_cost"}:
            if value is not None and (type(value) not in {int, float} or value < 0):
                raise ValidationError("Invalid nonnegative measurement")
        elif key == "raw_usage":
            # Provider usage numeric fields only; preserve their nested shape.
            def check(item: Any) -> None:
                if isinstance(item, dict):
                    for name, val in item.items():
                        if not isinstance(name, str) or len(name) > 100:
                            raise ValidationError("Invalid usage field")
                        check(val)
                elif item is not None and (type(item) is not int or item < 0):
                    raise ValidationError("Raw usage accepts only numeric counters")
            check(value)
        elif value is not None and (not isinstance(value, str) or len(value) > 256):
            raise ValidationError("Telemetry labels must be short strings, not raw content")
    if len(dumps(clean).encode()) > 16_384:
        raise ValidationError("Event size limit")
    return clean


class Telemetry:
    def __init__(self, path: Path, *, max_events: int = 100_000, retention_days: int = 30):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=0.05)
        path.chmod(0o600)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript((Path(__file__).parent / "migrations/001_events.sql").read_text())
        if self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] != "1":
            raise ValidationError("Unsupported telemetry schema")
        self.lock = threading.RLock()
        self.max_events, self.retention_days = max_events, retention_days
        self.drops = 0
        self.errors = 0
        self.cleanup()

    def emit(self, workspace: str, mode: str, run_id: str, kind: str, data: dict[str, Any], access: Access, *,
             event_id: str | None = None, timestamp: float | None = None, request_id: str | None = None, revision: int = 0) -> str | None:
        access.require(workspace)
        if mode not in {"real", "demo"} or type(revision) is not int or revision < 0:
            raise ValidationError("Invalid event envelope")
        clean = sanitize(kind, data)
        event_id = event_id or uuid4().hex
        for value in (workspace, run_id, event_id, request_id or "none"):
            if not isinstance(value, str) or not 1 <= len(value) <= 128:
                raise ValidationError("Invalid event identifier")
        if kind == "usage" and not request_id:
            raise ValidationError("Each model request needs a stable request ID")
        try:
            with self.lock, self.db:
                if self.db.execute("SELECT 1 FROM events WHERE event_id=?", (event_id,)).fetchone():
                    return event_id
                if self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0] >= self.max_events:
                    self.drops += 1
                    return None
                self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (event_id, workspace, mode, run_id, kind, timestamp if timestamp is not None else time.time(), time.time(), request_id, revision, dumps(clean)))
        except sqlite3.OperationalError:
            self.drops += 1
            self.errors += 1
            return None
        return event_id

    def sink(self, workspace: str, mode: str, run_id: str, access: Access):
        return lambda kind, data, **kwargs: self.emit(workspace, mode, run_id, kind, data, access, **kwargs)

    def events(self, scope: Scope, access: Access) -> list[dict[str, Any]]:
        access.require(scope.workspace)
        with self.lock:
            rows = self.db.execute("SELECT event_id,run_id,kind,timestamp,received,request_id,revision,data FROM events WHERE workspace=? AND mode=? ORDER BY timestamp,event_id", (scope.workspace, scope.mode)).fetchall()
        events = [{"event_id": r[0], "run_id": r[1], "kind": r[2], "timestamp": r[3], "received": r[4], "request_id": r[5], "revision": r[6], "data": strict_loads(r[7])} for r in rows]
        # Filter entire run cohort by run start, never lop retry/usage events off a task.
        runs: dict[str, dict[str, Any]] = {}
        for e in sorted(events, key=lambda x: (x["revision"], x["timestamp"])):
            if e["kind"] == "run":
                runs[e["run_id"]] = e["data"]
        selected = set()
        for run_id, run in runs.items():
            start = run.get("start", 0)
            if scope.start is not None and start < scope.start or scope.end is not None and start > scope.end:
                continue
            if any(run.get(key) != val for key, val in scope.filters.items()):
                continue
            if scope.search.casefold() not in (run_id + " " + run.get("task", "")).casefold():
                continue
            selected.add(run_id)
        return [e for e in events if e["run_id"] in selected]

    def cleanup(self) -> int:
        removed = 0
        with self.lock, self.db:
            workspaces = self.db.execute("SELECT DISTINCT workspace FROM events").fetchall()
            for (workspace,) in workspaces:
                row = self.db.execute("SELECT data FROM settings WHERE workspace=?", (workspace,)).fetchone()
                days = strict_loads(row[0])["retention_days"] if row else self.retention_days
                cutoff = time.time() - days * 86400
                removed += self.db.execute("DELETE FROM events WHERE workspace=? AND (mode,run_id) IN (SELECT mode,run_id FROM events WHERE workspace=? GROUP BY mode,run_id HAVING MAX(received) < ?)", (workspace, workspace, cutoff)).rowcount
        return removed

    def settings(self, workspace: str, access: Access, value: dict[str, Any] | None = None) -> dict[str, Any]:
        access.require(workspace)
        defaults = {"retention_days": 30, "timezone": "UTC", "prices": [], "alerts": {"min_samples": 5, "success_rate_below": 0.95, "retry_rate_above": 0.2, "latency_ms_above": 30000, "cost_per_success_above": 1.0, "retrieval_failure_rate_above": 0.05, "validation_failure_rate_above": 0.05, "coverage_below": 0.95}}
        if value is not None:
            from .metrics import validate_settings
            validate_settings(value)
            with self.lock, self.db:
                self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (workspace, dumps(value)))
            # Scope-specific retention; keep other workspaces intact.
            with self.lock, self.db:
                self.db.execute("DELETE FROM events WHERE workspace=? AND (mode,run_id) IN (SELECT mode,run_id FROM events WHERE workspace=? GROUP BY mode,run_id HAVING MAX(received)<?)", (workspace, workspace, time.time()-value["retention_days"]*86400))
        with self.lock:
            row = self.db.execute("SELECT data FROM settings WHERE workspace=?", (workspace,)).fetchone()
        return strict_loads(row[0]) if row else defaults

    def close(self) -> None:
        self.db.close()
