# Versioned interfaces · v1

## Python SDK

- `Manifest.create(data) -> Manifest`: validates the published manifest schema plus source hashes, unique requirement IDs and dependency closure references. Immutable serialized body and SHA-256 version.
- `Engine.prepare_context(manifest, task, required_ids, output_contract, ...) -> dict`: resolves exact requirement scope. References require this Engine's access and current store.
- `Registry.encode(suite, stop_after=1) -> dict`: direct compact command object. `schema()` / `description()` expose exact trusted defaults and version.
- `Registry.expand(request, system=None) -> Invocation`: immutable argv/cwd/version/digest; no execution. `dry_run()` adds readable platform-appropriate display.
- `Registry.choose_interface(request, tokenizer, expected_calls=1) -> dict`: compare owned native/compact schemas + instructions + expected calls before model generation. Invalid requests still fail when tokenizer is unavailable.
- `Registry.execute(request, approve=host_callback, timeout=60)`: exactly one host-approved subprocess; no shell, execution deduplication, or retry.
- `Engine.expand_command(...)` / `Engine.execute_command(...)`: correlated metadata wrappers, raw arguments redacted from telemetry; return full invocation/result to the authorized host.
- `Engine.optimize(text, format='auto', signed=False, exact_dataset=False, max_tokens=None, exit_status=None) -> Optimization`: `message()` is the model-visible role/trust/content/optional reference/exit-status envelope; `metadata()` is an operator result including method, counts, basis, warning, duration and bypass reason. Do not add the complete metadata object to each model prompt.
- `Engine.retrieve(reference) -> dict`: exact retained content, original role, untrusted-data trust tag and immutable source version. Explicit error if missing/expired/corrupt/unauthorized.
- `Telemetry.emit(workspace, mode, run_id, kind, data, access, event_id=..., request_id=..., revision=...)`: host-controlled metadata ingestion. Returns event ID, or null on capacity/busy drop. No HTTP public ingestion endpoint.
- `Telemetry.events(scope, access)` and `metrics.summarize(events, scope, settings)`: same backend aggregation used by CLI and dashboard.

Schema files are packaged under `src/agent_context_engine/schemas/`. Dynamic suite enums and registry version constants are supplied by `Registry.schema()`, with stricter runtime path/contract validation. Event data field allowlists and type constraints live in `telemetry.sanitize`; the published event JSON schema documents the envelope and per-kind allowed keys. JSON schema alone does not express access controls, source integrity or exact command authority.

## HTTP read API

All routes except static assets and login require a current local session and host-authorized workspace.

- `POST /api/login`: JSON `{"secret":"operator-supplied-local-secret"}`, exact Origin; establishes HttpOnly session. No query credentials.
- `GET /api/summary`: complete selected-scope aggregate.
- `GET /api/runs/{run_id}`: selected-scope metadata trace; never executes or reveals unretained raw text.
- `GET /api/options`: authorized workspace options and dimension choices within one mode/workspace.
- `GET /api/health`: scoped local measurement availability and process diagnostics.
- `GET /api/settings`, `POST /api/settings`: selected workspace retention/timezone/prices/advisory thresholds.
- `GET /api/export.json`, `/api/export.csv`, `/api/report.html`: same scope, mode labels and metadata only.

Query parameters: `workspace`, `mode` (`real` default, or `demo`), `start`/`end` (Unix seconds filtering **run start** while retaining the complete run), `search` (task label/run ID), `agent`, `provider`, `model`, `engine_version`, `method`, `tokenizer`, `arm`, `benchmark`. Unknown/duplicate query fields are rejected. Every card/table/export uses the same query. No mutation/execution API or raw-content endpoint exists.

Unknown metrics are JSON null with reasons or coverage; not zero. Evidence source and paired-comparison method are separate fields. Alert thresholds are absolute advisory checks in v0.1; no automatic model/permission/policy changes are possible.

## Model interfaces

The minimal stdio MCP own-tool list is documented in INTEGRATIONS. There is no universal middleware hook. Responses is a non-streaming, host-approved custom-function adapter; preservation of its exact call IDs and opaque output history is covered by tests. Schema definitions and wrappers sent to a model must be included in real workflow accounting.
