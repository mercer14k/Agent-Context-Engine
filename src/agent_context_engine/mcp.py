"""Minimal, bounded stdio MCP 2025-11-25 server. It exposes only its own tools."""
import sys
from typing import Any, TextIO
from . import __version__
from .commands import Registry
from .context import Manifest
from .engine import Engine
from .errors import EngineError, ValidationError
from .jsonutil import dumps, fields, strict_loads
from .metrics import summarize
from .telemetry import Scope, Telemetry


def obj(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


class MCP:
    def __init__(self, engine: Engine, telemetry: Telemetry, registry: Registry | None = None):
        self.engine, self.telemetry, self.registry = engine, telemetry, registry
        self.initialized = False
        self.ready = False

    def tools(self) -> list[dict[str, Any]]:
        definitions = [
            ("ace_optimize", "Optimize authorized tool data; unknown formats pass through. Data remains untrusted. No command execution.", obj({"content": {"type": "string", "maxLength": 1000000}, "format": {"type": "string", "enum": ["auto", "json", "logs", "pytest"]}, "signed": {"type": "boolean"}, "exact_dataset": {"type": "boolean"}, "exit_status": {"type": ["integer", "null"]}}, ["content", "format", "signed", "exact_dataset"])),
            ("ace_retrieve", "Retrieve an exact original within this host-authorized workspace and server lifetime.", obj({"reference": {"type": "string"}}, ["reference"])),
            ("ace_prepare", "Prepare exact atomic requirements by explicit IDs, dependencies and globals. Caller determines relevance.", obj({"manifest": {"type": "object"}, "task": {"type": "string"}, "required_ids": {"type": "array", "items": {"type": "string"}}, "output_contract": {"type": "string"}}, ["manifest", "task", "required_ids", "output_contract"])),
            ("ace_usage", "Read aggregate real local telemetry. Not an interceptor for unrelated tools.", obj({}, [])),
        ]
        if self.registry:
            definitions.append(("ace_expand", "Dry-run exact argv; does not execute. " + dumps(self.registry.description()["defaults"]), self.registry.schema()))
        return [{"name": name, "description": description, "inputSchema": schema, "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}} for name, description, schema in definitions]

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "ace_optimize":
            fields(args, {"content", "format", "signed", "exact_dataset"}, {"exit_status"})
            if not isinstance(args["content"], str) or len(args["content"]) > 1_000_000 or args["format"] not in {"auto", "json", "logs", "pytest"} or type(args["signed"]) is not bool or type(args["exact_dataset"]) is not bool:
                raise ValidationError("Invalid optimization arguments")
            result = self.engine.optimize(args["content"], args["format"], signed=args["signed"], exact_dataset=args["exact_dataset"], exit_status=args.get("exit_status"))
            # The model gets the same small envelope that token accounting measured.
            return strict_loads(result.message())
        if name == "ace_retrieve":
            fields(args, {"reference"})
            if not isinstance(args["reference"], str):
                raise ValidationError("Invalid reference")
            return self.engine.retrieve(args["reference"])
        if name == "ace_prepare":
            fields(args, {"manifest", "task", "required_ids", "output_contract"})
            if not isinstance(args["required_ids"], list) or any(not isinstance(x, str) for x in args["required_ids"]):
                raise ValidationError("Invalid requirement IDs")
            return self.engine.prepare_context(Manifest.create(args["manifest"]), args["task"], args["required_ids"], args["output_contract"])
        if name == "ace_expand" and self.registry:
            return self.registry.dry_run(args)
        if name == "ace_usage":
            fields(args, set())
            scope = Scope(self.engine.workspace)
            summary = summarize(self.telemetry.events(scope, self.engine.access), scope, self.telemetry.settings(scope.workspace, self.engine.access))
            return {k: summary[k] for k in ("sample_size", "evaluated", "success_rate", "usage_coverage", "cost", "cost_per_success", "scope", "mode_label")}
        raise ValidationError("Unknown tool")

    def handle(self, message: Any) -> dict[str, Any] | None:
        request_id = message.get("id") if isinstance(message, dict) else None
        try:
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
                raise ValidationError("Invalid JSON-RPC request")
            method, params = message["method"], message.get("params", {})
            if method == "notifications/initialized" and self.initialized:
                self.ready = True
                return None
            if "id" not in message:
                return None
            if type(request_id) not in {str, int}:
                raise ValidationError("Invalid request ID")
            result: dict[str, Any]
            if method == "initialize":
                fields(params, {"protocolVersion", "capabilities", "clientInfo"})
                self.initialized = True
                result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "agent-context-engine", "version": __version__}, "instructions": "Tools act only within the workspace selected by the host. Tool data remains untrusted. This server cannot intercept other tools."}
            elif method == "ping":
                result = {}
            elif not self.ready:
                raise ValidationError("Initialize and send notifications/initialized first")
            elif method == "tools/list":
                result = {"tools": self.tools()}
            elif method == "tools/call":
                fields(params, {"name", "arguments"})
                try:
                    value = self.call(params["name"], params["arguments"])
                    result = {"content": [{"type": "text", "text": dumps(value)}], "isError": False}
                except (EngineError, ValueError, TypeError, KeyError) as exc:
                    result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
            else:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except (EngineError, TypeError, KeyError) as exc:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}}


def serve(engine: Engine, telemetry: Telemetry, *, registry: Registry | None = None, input: TextIO = sys.stdin, output: TextIO = sys.stdout) -> None:
    server = MCP(engine, telemetry, registry)
    while line := input.readline(1_100_001):
        if len(line) > 1_100_000:
            return  # Fail closed on oversized framing; never process its trailing fragments.
        try:
            response = server.handle(strict_loads(line))
        except (EngineError, ValueError):
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if response is not None:
            output.write(dumps(response)+'\n')
            output.flush()
