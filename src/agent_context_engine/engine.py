from dataclasses import asdict, dataclass, field
import time
from typing import Any, Callable
from uuid import uuid4
from .context import Manifest
from .errors import EngineError
from .jsonutil import dumps
from .store import Access, ReferenceStore
from .tokens import Tokenizer
from .transforms import transform


@dataclass
class Optimization:
    method: str
    content: str
    source_version: str = "v1"
    role: str = "tool"
    trust: str = "untrusted_data"
    exit_status: int | None = None
    raw_reference: str | None = None
    original_tokens: int | None = None
    optimized_tokens: int | None = None
    token_basis: str = "Unavailable"
    model_mapping: str = "Unavailable"
    measurement_scope: str = "Complete model-visible result envelope, including reference and trust wrapper"
    warnings: list[str] = field(default_factory=list)
    bypass_reason: str | None = None
    duration_ms: float = 0

    def message(self) -> str:
        return dumps({"role": self.role, "trust": self.trust, "content": self.content,
                      **({"exit_status": self.exit_status} if self.exit_status is not None else {}),
                      **({"raw_reference": self.raw_reference} if self.raw_reference else {})})

    def metadata(self) -> dict[str, Any]:
        return asdict(self)


class Engine:
    def __init__(self, workspace: str, access: Access, *, tokenizer: Tokenizer | None = None,
                 store: ReferenceStore | None = None, emit: Callable[..., Any] | None = None):
        access.require(workspace)
        self.workspace, self.access = workspace, access
        self.tokenizer = tokenizer
        self.store = store or ReferenceStore()
        self.emit = emit

    def optimize(self, text: str, format: str = "auto", *, signed: bool = False,
                 exact_dataset: bool = False, max_tokens: int | None = None, exit_status: int | None = None) -> Optimization:
        self.access.require(self.workspace)
        if exit_status is not None and type(exit_status) is not int:
            from .errors import ValidationError
            raise ValidationError("Exit status must be an integer or unavailable")
        start = time.perf_counter()
        result = Optimization("passthrough", text, exit_status=exit_status)
        original_message = result.message()
        try:
            if signed or format in {"shell", "sql", "code", "regex", "patch", "formula", "stream", "reasoning"}:
                result.bypass_reason = "Protected content must pass through unchanged"
            elif self.tokenizer is None:
                result.bypass_reason = "Tokenizer unavailable; no token-benefit claim"
            elif len(text.encode()) > self.store.max_bytes:
                result.bypass_reason = "Payload exceeds configured processing limit"
            else:
                candidate, method, selective = transform(text, format)
                if candidate == text:
                    result.bypass_reason = "Unsupported format or already compact"
                elif selective and exact_dataset:
                    result.bypass_reason = "Selective view prohibited for exhaustive task"
                else:
                    trial = Optimization(method, candidate, exit_status=exit_status)
                    if selective:
                        trial.raw_reference = self.store.put(self.workspace, text, self.access)
                        # Check before issuing; later expiration still handled during retrieval.
                        self.store.get(self.workspace, trial.raw_reference, self.access)
                        trial.warnings = ["Selective view; retrievable original does not prove model awareness"]
                    if self.tokenizer.count(trial.message()) >= self.tokenizer.count(original_message):
                        result.bypass_reason = "Wrapper/reference overhead exceeds reduction"
                    elif max_tokens is not None and self.tokenizer.count(trial.message()) > max_tokens:
                        result.bypass_reason = "Required details cannot fit budget"
                    else:
                        result = trial
        except (EngineError, ValueError, OSError, RecursionError):
            result = Optimization("passthrough", text, exit_status=exit_status, bypass_reason="Optimization validation failed; unchanged authorized data")
        if self.tokenizer:
            try:
                result.original_tokens = self.tokenizer.count(original_message)
                result.optimized_tokens = self.tokenizer.count(result.message())
                result.token_basis = self.tokenizer.identity
                result.model_mapping = self.tokenizer.model_mapping
            except (ValueError, OSError):
                result = Optimization("passthrough", text, exit_status=exit_status, bypass_reason="Tokenizer failed; unchanged data")
        result.duration_ms = (time.perf_counter() - start) * 1000
        if self.emit:
            self.emit("optimization", {"method": result.method, "original_tokens": result.original_tokens,
                    "optimized_tokens": result.optimized_tokens, "tokenizer": result.token_basis,
                    "duration_ms": result.duration_ms, "bypass_reason": result.bypass_reason,
                    "evidence": "Tokenizer-counted payload" if result.original_tokens is not None else "Unavailable"})
        return result

    def prepare_context(self, manifest: Manifest, task: str, required_ids: list[str], output_contract: str, **kwargs: Any) -> dict[str, Any]:
        return manifest.prepare(task, required_ids, output_contract, store=self.store, workspace=self.workspace, access=self.access, **kwargs)

    def retrieve(self, reference: str) -> dict[str, str]:
        start = time.perf_counter()
        try:
            result = self.store.get(self.workspace, reference, self.access)
        except EngineError:
            if self.emit:
                self.emit("retrieval", {"valid": False, "duration_ms": (time.perf_counter()-start)*1000})
            raise
        if self.emit:
            self.emit("retrieval", {"valid": True, "duration_ms": (time.perf_counter()-start)*1000})
        return result

    def expand_command(self, registry: Any, request: dict[str, Any]) -> dict[str, Any]:
        """Dry-run with metadata-only tracing. Registry is supplied by trusted host."""
        start = time.perf_counter()
        try:
            result = registry.dry_run(request)
        except (EngineError, OSError):
            if self.emit:
                self.emit("command", {"operation": "run_tests", "valid": False, "executed": False, "schema_version": "1"})
            raise
        choice = registry.choose_interface(request, self.tokenizer)
        if self.emit:
            self.emit("command", {"operation": "run_tests", "schema_version": "1", "registry_version": registry.version,
                      "valid": True, "executed": False, "arguments": request, "invocation": result["argv"],
                      "request_digest": result["request_digest"], "duration_ms": (time.perf_counter()-start)*1000,
                      "compact_tokens": choice["compact_tokens"], "native_tokens": choice["native_tokens"]})
        return {**result, "interface_selection": choice}

    def execute_command(self, registry: Any, request: dict[str, Any], *, approve: Callable[..., bool], timeout: float = 60) -> Any:
        """One host-approved execution; metadata only. Never retry on any failure."""
        start = time.perf_counter()
        invocation = registry.expand(request)
        try:
            result = registry.execute(request, approve=approve, timeout=timeout)
        except Exception:
            if self.emit:
                self.emit("command", {"operation": "run_tests", "schema_version": "1", "registry_version": registry.version, "request_digest": invocation.request_digest,
                          "valid": True, "executed": None, "exit_code": None, "duration_ms": (time.perf_counter()-start)*1000})
            raise
        if self.emit:
            self.emit("command", {"operation": "run_tests", "schema_version": "1", "registry_version": registry.version, "request_digest": invocation.request_digest,
                      "valid": True, "executed": True, "exit_code": result.returncode, "duration_ms": (time.perf_counter()-start)*1000})
        return result
