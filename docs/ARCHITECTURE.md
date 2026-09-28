# Architecture and boundaries · v0.1

## Data path

1. A trusted host creates `Access(principal, workspaces)` and binds an Engine to one workspace. This object is never parsed from model fields.
2. `Manifest.create` validates atomic structured requirements and hashes immutable source/manifest versions. Task preparation selects caller-specified IDs plus dependency closure and globals. Exact source strings survive. No arbitrary prose summarization, extraction, or equivalence proof is implemented.
3. A host-owned `Registry` resolves suite aliases, Python executable, cwd and fixed pytest arguments. The exposed schema has version/registry checks, integer limits and explicit defaults. Expansion returns an exact tuple. Shell display is advisory; subprocess receives argv with `shell=False`.
4. `Engine.optimize` chooses a small supported transform and counts the complete result envelope. It bypasses when counts are unavailable, overhead dominates, exact-dataset policy prohibits a selective view, required output cannot fit, or transform validation fails.
5. Metadata-only events enter SQLite. Request revisions replace cumulative snapshots; diagnostic transform counts are not added to model usage. Python SDK, CLI exports and HTTP routes share `metrics.summarize`.
6. The loopback dashboard fetches bounded local analytics every 15 seconds. No model, external font, CDN, mandatory GPU, frontend dev server or upload is required.

## Transform fidelity

- **JSON whitespace**: validates JSON with Decimal numeric parsing and duplicate-key rejection, then removes only whitespace outside quoted strings. Numbers, exponent forms, negative zero, string escapes, key/array order, booleans and null remain exact. This preserves values and lexical payload tokens, not original formatting bytes. No field projection is implemented. Signed JSON requires explicit `signed=True`; automatic signature detection is not claimed.
- **Adjacent log runs**: JSON run-length representation with exact original line (including timestamp and newline), count, start and end positions. `restore_logs` reconstructs the exact text with a decoded-size bound. Nonadjacent lines never merge. A timestamp changing makes a different line; no timestamp is stripped to inflate reduction.
- **Pytest progress view**: only a recognized terminal summary plus standalone progress rows is eligible. All other lines remain verbatim, including error sections and final counts. This is a **selective view**, with an integrity-checked original reference and explicit warning. It is not a mathematically lossless visible representation. Original retention does not prove model awareness. Unknown pytest variants pass through.
- Unknown or protected content is unchanged. No semantic rewrite backend exists in v0.1.

## Execution permissions

Invalid/stale commands raise errors before approval or execution. A `Registry.execute` host callback sees the exact expanded invocation. Validation repeats after approval, then one subprocess executes once. The engine does not retry execution or cache results. Repeated calls execute repeatedly. Never expose the approval callback through model arguments.

An argv interface is **not a sandbox**: project tests and plugins execute arbitrary code. Use the host's approvals or a trusted disposable fixture workspace. Registry roots/executables/configuration must be trusted. Symlink resolution checks containment at expansion time; filesystem changes by other processes after validation remain a host isolation concern. Environment isolation, OS sandboxing, network restrictions, process-tree termination, and unbounded subprocess stdout protection are not provided by this registry. Default timeout is 60 seconds; callers may configure it.

## Storage and trust

Raw originals live in memory by default. They expire (default one hour), have a 16 MB aggregate size bound, are immutable and receive SHA-256 integrity checks. References include unique version IDs plus content hashes. A hash is not authorization. Every put/get checks a host-created workspace capability, and retrieval queries both workspace and reference. Cross-workspace deduplication is not performed.

CLI processes are short-lived: pytest selective views require `--persist-originals` or return unchanged data. Persistent originals are plaintext SQLite, chmod 0600 where supported; directory modes are best effort on Windows. No encryption/key management is implemented. Local disk/OS account access can read retained data. Memory defaults avoid permanent prompt capture; no raw-content redaction is claimed for originals. Stored originals are exact. Raw diff UI is intentionally unavailable.

Metadata uses an allowlist and excludes raw prompts, executable arguments, API keys, private reasoning and response bodies. Command argument/invocation fields are replaced with a redaction marker. Caller-provided short task/agent/config labels must be non-sensitive identifiers: this is not a universal secret detector. Provider `raw_usage` allows only nested numeric counters. Logs never print HTTP request bodies or credentials.

Tool/retrieved data remains role-marked `untrusted_data`; it is not promoted to system/developer instructions. Manifest user requirements remain separate from documents and tool outputs. Python SDK access objects cannot defend against malicious code in the same process/OS account; the trusted host owns that boundary.

## Dashboard isolation

The server binds only `127.0.0.1`, accepts the exact loopback Host and same-origin browser requests, denies cross-origin POSTs, bounds request bodies, rate-limits login, and uses a random expiring HttpOnly SameSite=Strict cookie. The login secret is entered in a POST body, never a URL. No credentials are included in JavaScript assets or exports. HTTP is limited to loopback; it is not TLS or protection from malware under the same OS user.

Every sensitive backend route checks session and workspace `Access`. The CLI grants only its `--workspace`; SDK applications may grant an explicit set. UI filters never grant access. Trace/detail/export routes are read-only; no execution endpoint exists. Dynamic text uses DOM text nodes, HTML reports escape strings, and CSV formula prefixes are neutralized. Exports are metadata-only, carry data mode/scope and never include raw content.

## Event and performance limits

Events are at most 16 KB, with a default 100,000-event database cap. SQLite WAL and a 50 ms busy timeout bound write waits; full/busy ingestion drops events and increments visible in-process counters. Analytics read a bounded event set. Raw transforms cap input bytes at the store limit. No asynchronous work is required to use the engine. More advanced background analytics, durable event-drop counters, process-tree monitoring and large output handling are roadmap items; avoid high-throughput multi-process production use until measured.

Retention cleanup deletes whole cohorts to avoid silently dropping retries from tasks. Settings persist and workspace-specific retention applies on subsequent cleanup/restart. Logical deletion is not forensic secure erasure; SQLite free pages, WAL, backups and OS snapshots may retain bytes. No automatic raw backups are made. Explicit CSV/JSON reports are the safe metadata export path.

Tool exit status is a separate integer supplied by the host (`exit_status`); it survives transforms and bypass in the counted model-visible envelope. The engine never infers an exit code from text. Unknown exit status remains absent/unavailable. `Engine.execute_command` records a correlated execution outcome without retry; on exceptions it reports execution state unknown because timeouts can occur after a command started.
