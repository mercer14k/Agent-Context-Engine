# Runtime boundaries

CLI: `ace registry` exposes registered suites and exact defaults; `ace expand` is dry-run only. `Registry.execute(request, approve=host_callback)` requires a host callback bound to the exact expanded invocation. It executes no shell and retries nothing. Project tests remain arbitrary code; approval must come from the host's existing policy or a trusted isolated fixture workspace.

MCP: `ace_optimize`, `ace_retrieve`, `ace_prepare`, `ace_usage`; `ace_expand` is available only if the host supplied a Registry. The CLI can supply one via `ace mcp --root PROJECT --suites SUITES_JSON`. A stdio session owns one host-configured workspace and memory-only original store. Its references expire and do not survive server exit.

No automatic host hooks are bundled. Register the installed `ace` executable and workspace state path using the host's supported MCP configuration. Do not assume an MCP connection intercepts other tool output. Opt in to persistent raw originals only when necessary and permitted; no encryption is implemented.

Compact requests are v1 JSON with `v`, `registry`, `op="run_tests"`, `suite`, optional `stop_after` (default 1). The schema and default executable, fixed `-m pytest -q`, suite path and cwd must be visible before choosing this interface. Use `Registry.choose_interface` to compare complete definitions plus expected calls against a native argv tool. This cannot refund generated text.
