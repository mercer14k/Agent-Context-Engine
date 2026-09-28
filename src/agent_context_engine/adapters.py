"""Small Responses wire adapter and real offline loop. No model is required by core."""
from dataclasses import dataclass
import json
import time
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4
from . import __version__
from .engine import Engine
from .errors import AccessDenied, ValidationError
from .fixtures import inventory, inventory_result
from .jsonutil import strict_loads, dumps
from .store import Access
from .telemetry import Telemetry
from .tokens import Tokenizer


def normalize_responses_usage(usage: dict[str, Any] | None, *, model: str, price_version: str | None = None) -> dict[str, Any]:
    u = usage or {}
    details = u.get("input_tokens_details") or {}
    output_details = u.get("output_tokens_details") or {}
    return {"provider": "openai", "model": model, "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
        "cached_input_tokens": details.get("cached_tokens"), "cache_write_tokens": 0,
        "reasoning_tokens": output_details.get("reasoning_tokens"), "raw_usage": u,
        "tool_cost": 0, "final": usage is not None, "purpose": "operation", "evidence": "Provider-reported usage" if usage is not None else "Unavailable", "price_version": price_version}


class ResponsesAdapter:
    """Non-streaming, custom-function-only API. Host explicitly approves each request.

    API transport has no automatic retry: ambiguous network failures may be billable.
    A live trial runner with spend reservations is separate roadmap work.
    """
    def __init__(self, *, model: str, api_key: str, approve: Callable[[dict[str, Any]], bool],
                 base_url: str = "https://api.openai.com/v1", max_output_tokens: int = 512,
                 emit: Callable[..., Any] | None = None, price_version: str | None = None,
                 transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None):
        parts = urlsplit(base_url)
        if parts.scheme != "https" or parts.username or parts.password or parts.query or parts.fragment:
            raise ValidationError("Provider endpoint must be HTTPS without URL credentials or query")
        if not model or not api_key or type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 32768:
            raise ValidationError("Model, key, and bounded output limit required")
        self.model, self.key, self.approve = model, api_key, approve
        self.base_url, self.max_output_tokens = base_url.rstrip('/'), max_output_tokens
        self.emit, self.price_version, self.transport = emit, price_version, transport

    def create(self, inputs: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if any(t.get("type") != "function" for t in tools):
            raise ValidationError("Only local custom function tools supported; billable built-ins excluded")
        payload = {"model": self.model, "input": inputs, "tools": tools, "max_output_tokens": self.max_output_tokens, "stream": False, "store": False}
        if not self.approve(payload):
            raise AccessDenied("Provider request denied by host")
        start = time.perf_counter()
        request_id = uuid4().hex
        try:
            if self.transport:
                response = self.transport(payload)
            else:
                req = Request(self.base_url+'/responses', data=dumps(payload).encode(), headers={"Authorization": 'Bearer '+self.key, "Content-Type": "application/json"}, method="POST")
                with urlopen(req, timeout=60) as stream:
                    raw = stream.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise ValidationError("Provider response size limit")
                response = strict_loads(raw.decode())
            if not isinstance(response, dict) or not isinstance(response.get("output"), list):
                raise ValidationError("Unsupported Responses response")
        except Exception:
            if self.emit:
                self.emit("usage", normalize_responses_usage(None, model=self.model, price_version=self.price_version), request_id=request_id)
            raise
        if self.emit:
            usage = normalize_responses_usage(response.get("usage"), model=self.model, price_version=self.price_version)
            usage["provider_wait_ms"] = (time.perf_counter()-start)*1000
            self.emit("usage", usage, request_id=response.get("id") or request_id, revision=1)
        return response


def agent_loop(create: Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]], engine: Engine, *, max_steps: int = 4) -> dict[str, Any]:
    """Read-only synthetic inventory integration. Full output items remain opaque."""
    tool = {"type": "function", "name": "read_inventory", "description": "Read the complete synthetic inventory dataset. Preserve all rows and exact decimals.", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "strict": True}
    inputs: list[dict[str, Any]] = [{"role": "user", "content": "Reconcile every inventory row. Return a JSON object with items, closing_total, valuation as an exact decimal string, and mismatches."}]
    for _ in range(max_steps):
        response = create(inputs, [tool])
        items = response["output"]
        # Includes opaque reasoning items and signatures verbatim, never inspected or logged.
        inputs.extend(items)
        calls = [item for item in items if item.get("type") == "function_call"]
        if not calls:
            texts = [part["text"] for item in items if item.get("type") == "message" for part in item.get("content", []) if part.get("type") == "output_text"]
            if not texts:
                raise ValidationError("No final answer")
            return strict_loads("".join(texts), decimals=True)
        for call in calls:
            if call.get("name") != "read_inventory" or strict_loads(call["arguments"]) != {} or not isinstance(call.get("call_id"), str):
                raise ValidationError("Invalid tool call; nothing executed")
            result = engine.optimize(inventory(), "json", exact_dataset=True)
            inputs.append({"type": "function_call_output", "call_id": call["call_id"], "output": result.message()})
    raise ValidationError("Agent step limit; no automatic replay of tools")


def offline_agent(db: Telemetry, workspace: str, access: Access, tokenizer: Tokenizer | None) -> dict[str, Any]:
    run_id = uuid4().hex
    sink = db.sink(workspace, "real", run_id, access)
    start = time.time()
    engine = Engine(workspace, access, tokenizer=tokenizer, emit=sink)
    requests = 0
    def mock(inputs: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        nonlocal requests
        requests += 1
        if requests == 1:
            return {"output": [{"type": "function_call", "name": "read_inventory", "arguments": "{}", "call_id": "offline-call-1"}]}
        full_result = strict_loads(inputs[-1]["output"])["content"]
        answer = inventory_result(full_result)
        return {"output": [{"type": "message", "content": [{"type": "output_text", "text": dumps(answer)}]}]}
    answer = agent_loop(mock, engine)
    success = answer == {"items": 40, "closing_total": 4200, "valuation": "518.518513851851851384200", "mismatches": []}
    sink("run", {"task": "offline-inventory-loop", "agent": "offline-mock", "provider": "none", "model": "mock", "tokenizer": tokenizer.identity if tokenizer else "Unavailable", "benchmark": "offline-agent", "arm": "engine", "config": "mock-v1", "engine_version": __version__, "method": "json_whitespace", "start": start, "end": time.time(), "success": success, "validator": "exact-inventory-v1", "expected_requests": 0, "evidence": "Offline mock outcome"})
    sink("check", {"validator": "exact-inventory-v1", "category": "end_task", "valid": success, "evidence": "Offline mock outcome"})
    return {"run_id": run_id, "answer": answer, "verified_mock_success": success, "mock_steps": requests, "provider_calls": 0, "evidence": "Offline mock; not live agent quality"}
