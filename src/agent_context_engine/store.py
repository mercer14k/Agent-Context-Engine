"""Workspace-scoped immutable originals. In-memory by default; no encryption claim."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sqlite3
import threading
import time
from typing import Callable
from uuid import uuid4
from .errors import AccessDenied, ReferenceUnavailable, ValidationError


@dataclass(frozen=True)
class Access:
    """Created by trusted host code, never deserialized from model arguments."""
    principal: str
    workspaces: frozenset[str]

    def require(self, workspace: str) -> None:
        if workspace not in self.workspaces:
            raise AccessDenied("Workspace is not authorized")


class ReferenceStore:
    def __init__(self, path: Path | None = None, *, retention_seconds: float = 3600,
                 max_bytes: int = 16_000_000, clock: Callable[[], float] = time.time):
        if retention_seconds <= 0 or max_bytes <= 0:
            raise ValidationError("Retention and size limits must be positive")
        self.persistent = path is not None
        if path:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(str(path) if path else ":memory:", check_same_thread=False)
        if path:
            path.chmod(0o600)
        self.db.execute("CREATE TABLE IF NOT EXISTS originals (ref TEXT PRIMARY KEY, workspace TEXT, digest TEXT, body BLOB, role TEXT, expires REAL)")
        self.lock = threading.RLock()
        self.retention = retention_seconds
        self.max_bytes = max_bytes
        self.clock = clock

    def put(self, workspace: str, text: str, access: Access, *, role: str = "tool") -> str:
        access.require(workspace)
        if role not in {"tool", "document", "user"}:
            raise ValidationError("Originals cannot become system or developer policy")
        data = text.encode("utf-8")
        with self.lock, self.db:
            self.cleanup()
            size = self.db.execute("SELECT COALESCE(SUM(length(body)),0) FROM originals").fetchone()[0]
            if size + len(data) > self.max_bytes:
                raise ReferenceUnavailable("Local store size limit reached")
            digest = hashlib.sha256(data).hexdigest()
            ref = f"ace:v1:{uuid4().hex}:{digest}"
            self.db.execute("INSERT INTO originals VALUES (?,?,?,?,?,?)",
                            (ref, workspace, digest, data, role, self.clock() + self.retention))
            self.get(workspace, ref, access)
            return ref

    def get(self, workspace: str, ref: str, access: Access) -> dict[str, str]:
        access.require(workspace)
        with self.lock:
            row = self.db.execute("SELECT digest,body,role,expires FROM originals WHERE ref=? AND workspace=?", (ref, workspace)).fetchone()
            if row is None or row[3] <= self.clock():
                raise ReferenceUnavailable("Original missing, expired, or outside this workspace")
            digest, data, role, _ = row
            if hashlib.sha256(data).hexdigest() != digest:
                raise ReferenceUnavailable("Original integrity check failed")
            return {"content": data.decode("utf-8"), "role": role, "trust": "untrusted_data", "source_version": ref, "fidelity": "exact_original"}

    def cleanup(self) -> int:
        with self.lock, self.db:
            return self.db.execute("DELETE FROM originals WHERE expires<=?", (self.clock(),)).rowcount

    def stats(self) -> dict[str, int | bool]:
        with self.lock:
            row = self.db.execute("SELECT COUNT(*),COALESCE(SUM(length(body)),0),COALESCE(SUM(expires<=?),0) FROM originals", (self.clock(),)).fetchone()
            return {"entries": row[0], "bytes": row[1], "expired": row[2], "persistent": self.persistent}

    def close(self) -> None:
        self.db.close()
