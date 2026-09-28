"""Trusted registry -> exact argv. This is not an execution sandbox."""
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import platform
import shlex
import subprocess
import sys
from typing import Callable, Any
from .errors import AccessDenied, ValidationError
from .jsonutil import dumps, fields


@dataclass(frozen=True)
class Invocation:
    argv: tuple[str, ...]
    cwd: str
    platform: str
    registry_version: str
    request_digest: str

    @property
    def display(self) -> str:
        return subprocess.list2cmdline(self.argv) if self.platform == "Windows" else shlex.join(self.argv)


class Registry:
    def __init__(self, root: Path, suites: dict[str, str], *, python: str = sys.executable):
        self.root = root.resolve(strict=True)
        self.suites = dict(suites)
        self.python = python
        for key, value in suites.items():
            if not key or not isinstance(value, str):
                raise ValidationError("Invalid suite registry")
            path = (self.root / value).resolve(strict=True)
            if not path.is_relative_to(self.root):
                raise ValidationError("Suite escapes trusted workspace")
        self.version = hashlib.sha256(dumps({"v": 1, "root": str(self.root), "suites": suites, "python": python, "fixed": ["-m", "pytest", "-q"]}).encode()).hexdigest()[:16]

    def schema(self) -> dict[str, Any]:
        return {"type": "object", "additionalProperties": False,
                "properties": {"v": {"type": "integer", "const": 1},
                "registry": {"type": "string", "const": self.version},
                "op": {"type": "string", "const": "run_tests"},
                "suite": {"type": "string", "enum": sorted(self.suites)},
                "stop_after": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1}},
                "required": ["v", "registry", "op", "suite"]}

    def description(self) -> dict[str, Any]:
        return {"version": self.version, "schema": self.schema(), "defaults": {"stop_after": 1, "cwd": str(self.root), "executable": self.python, "fixed": ["-m", "pytest", "-q"], "suite_paths": self.suites}, "execution": "Host approval required; project tests execute arbitrary code"}

    def encode(self, suite: str, stop_after: int = 1) -> dict[str, Any]:
        request = {"v": 1, "registry": self.version, "op": "run_tests", "suite": suite, "stop_after": stop_after}
        self.expand(request)
        return request

    def expand(self, request: dict[str, Any], *, system: str | None = None) -> Invocation:
        fields(request, {"v", "registry", "op", "suite"}, {"stop_after"})
        system = system or platform.system()
        if system not in {"Darwin", "Linux", "Windows"}:
            raise ValidationError("Unsupported platform")
        if type(request["v"]) is not int or request["v"] != 1 or request["op"] != "run_tests":
            raise ValidationError("Unknown command version or operation")
        if request["registry"] != self.version:
            raise ValidationError("Stale registry version")
        suite = request["suite"]
        if not isinstance(suite, str) or suite not in self.suites:
            raise ValidationError("Unregistered suite")
        stop = request.get("stop_after", 1)
        if type(stop) is not int or not 1 <= stop <= 100:
            raise ValidationError("stop_after must be an integer from 1 to 100")
        path = (self.root / self.suites[suite]).resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise ValidationError("Stale or unsafe suite path")
        argv = (self.python, "-m", "pytest", "-q", f"--maxfail={stop}", "--", str(path))
        return Invocation(argv, str(self.root), system, self.version, hashlib.sha256(dumps(request).encode()).hexdigest())

    def execute(self, request: dict[str, Any], *, approve: Callable[[Invocation], bool], timeout: float = 60) -> subprocess.CompletedProcess[str]:
        invocation = self.expand(request)
        if not approve(invocation):
            raise AccessDenied("Execution denied by host")
        # Revalidate after approval; never retry execution or cache results.
        if self.expand(request) != invocation:
            raise ValidationError("Invocation changed after approval")
        return subprocess.run(invocation.argv, cwd=invocation.cwd, shell=False, capture_output=True, text=True, timeout=timeout)

    def dry_run(self, request: dict[str, Any]) -> dict[str, Any]:
        invocation = self.expand(request)
        return {**asdict(invocation), "display": invocation.display, "validation": "valid", "executed": False}

    def choose_interface(self, request: dict[str, Any], tokenizer: Any, *, expected_calls: int = 1) -> dict[str, Any]:
        """Count both owned interfaces, including exposed defaults/schema instructions.

        This is an interface-selection aid before generation; it cannot refund tokens.
        expected_calls amortizes definitions, never suppresses repeated execution.
        """
        invocation = self.expand(request)
        if type(expected_calls) is not int or expected_calls < 1:
            raise ValidationError("Expected call count must be positive")
        native_schema = {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}}, "cwd": {"type": "string"}}, "required": ["argv", "cwd"], "additionalProperties": False}
        native_call = {"argv": list(invocation.argv), "cwd": invocation.cwd}
        native_instruction = "Run exact argv in cwd after host approval; no shell. No retry or result reuse."
        if tokenizer is None:
            return {"interface": "native", "reason": "Tokenizer unavailable", "compact_tokens": None, "native_tokens": None, "native_call": native_call}
        compact = tokenizer.count(dumps(self.description())) + expected_calls * tokenizer.count(dumps(request))
        native = tokenizer.count(dumps(native_schema)+native_instruction) + expected_calls * tokenizer.count(dumps(native_call))
        return {"interface": "compact" if compact < native else "native", "reason": "Measured interface benefit" if compact < native else "Schema/default overhead exceeds reduction", "compact_tokens": compact, "native_tokens": native, "expected_calls": expected_calls, "tokenizer": tokenizer.identity, "measurement_scope": "Definitions + instructions + expected generated calls; excludes provider message framing and outcome", "native_call": native_call}
