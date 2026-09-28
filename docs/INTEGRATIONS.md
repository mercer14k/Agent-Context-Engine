# Integrations · v0.1

## SDK

Install `.` for dependency-free execution, `.[tokens]` for cached BPE counts. Examples are executable Python files, with no cloud calls unless the explicitly manual Responses example is invoked. Importing the SDK does not bind a port, create a database, or call a provider.

A host should create `Access`, `Telemetry`, a run ID, and a `sink`; pass that sink to `Engine` and `ResponsesAdapter`. Emit the final run record with expected model request count, validator identity and outcome. `Engine.expand_command` records redacted dry-run metadata. `Registry.execute` takes a host approval callback; hosts should record its execution outcome separately. Optional trace/span/parent IDs are supplied by the host. No universal interception is implied.

## OpenAI Responses

`ResponsesAdapter` uses the current documented non-streaming `/v1/responses` JSON shape: top-level function tools, `function_call` outputs, and `function_call_output` inputs tied to exact `call_id`. It uses standard HTTPS, configurable model/base URL, customer-provided keys, bounded output, `store:false`, and a required host callback before each request. Custom local functions only. The offline test transport exercised request construction, usage normalization, tool-call IDs, preserved opaque items and error paths; **no live provider request was made**.

Keys belong in the operator's environment or secret manager. They are never telemetry fields or browser assets. The loop passes all opaque output items back unchanged; it does not inspect or optimize private reasoning/signatures. Streaming, partial JSON, tool-call recovery, automatic network retries, other providers, built-in billable tools and transparent proxying are unsupported. An ambiguous timeout is not automatically retried because it may already have incurred cost.

`examples/responses_loop.py` requires `OPENAI_MODEL`, `OPENAI_API_KEY` and a typed approval for each request. Do not use it as a budgeted A/B runner: the spend-cap runner is a precise Phase 2 remaining task. No cloud calls are necessary for installation, tests or the dashboard.

## MCP stdio

Run the installed executable:

```sh
ace --state /absolute/private/project-state --workspace project-a mcp
```

On Windows set the process environment `PYTHONUTF8=1` for UTF-8 JSON files and stdio. Windows host configuration uses the absolute `...\.venv\Scripts\ace.exe` executable and absolute state path. macOS/Linux use `.../.venv/bin/ace`.

Optional trusted command registry:

```sh
ace --state /absolute/private/project-state --workspace project-a mcp --root /absolute/project --suites /absolute/project/examples/suites.json
```

Register this process through your host's supported MCP configuration. Representative stdio configuration (replace every path with your actual installed location):

```json
{
  "mcpServers": {
    "agent-context-engine": {
      "command": "/absolute/agent-context-engine/.venv/bin/ace",
      "args": ["--state", "/absolute/private/project-state", "--workspace", "project-a", "mcp"]
    }
  }
}
```

Codex config.toml uses the host's TOML `mcp_servers` form; it is not interchangeable with `.mcp.json`. See the official host documentation before applying settings. This repository does not edit installed host configuration. Use a distinct state path and workspace binding for unrelated customers.

The local server implements MCP 2025-11-25 initialize/version negotiation, initialized notification, ping, tools/list and tools/call over bounded UTF-8 newline-delimited JSON-RPC. stdout contains protocol messages only. It exposes `ace_optimize`, `ace_retrieve`, `ace_prepare`, `ace_usage`, and optional `ace_expand` (dry run only). Supported tools enforce exact arguments. It offers no transport-level remote access, resources subscriptions, sampling, tasks, arbitrary execution or hooks. Memory originals exist only during that server process and within its workspace.

MCP requests/results add framing and host metadata beyond the engine's counted inner payload envelope. Record actual host/provider usage for complete accounting. A host connection does not intercept unrelated tools, arbitrary application traffic or conversation history. In-process and actual subprocess framing tests passed; installation into the owner's interactive host remains untested.

## Skill and Codex packaging

The original Project Prompt Optimizer package was absent from the supplied project; v2 preserves the supplied brief's requirement safeguards. The canonical source is `skills/agent-context-engine/SKILL.md`; the packaged copy is under `integrations/codex/agent-context-engine/skills/agent-context-engine/`.

The plugin-creator scaffold and validator verified `.codex-plugin/plugin.json` with a skills surface. No host-hook or unsupported manifest fields are invented. The plugin intentionally contains behavior guidance only; runtime MCP registration requires the installed Python engine and a host-selected workspace, so no ambiguous automatic global MCP state path is bundled. No marketplace, installed plugin, existing repository or host setting was changed. Host installation/discovery acceptance is a remaining owner-host test.

Official sources and check dates are in [OFFICIAL-SOURCES](OFFICIAL-SOURCES.md). Plugin/skill format validation is not an assurance that a specific host has loaded it.
