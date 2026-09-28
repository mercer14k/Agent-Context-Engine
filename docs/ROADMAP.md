# Versioned delivery roadmap · 2026-09-15 · v0.1

This is the complete local vertical slice plus connected dashboard. The remaining items below are explicit scope, not removed requirements.

## Phase 1 — delivered developer preview

- Typed CPU-only core, SDK, CLI, immutable exact-text manifests, scoped handoffs, versioned command registry, exact argv expansion/host approval, memory-default reference store, conservative JSON/log/pytest transforms and bypass.
- Independent unit/integration/property tests, offline inventory agent loop, three-arm replay, interface-cost comparison and local instrumentation profile.
- Metadata events → migrated SQLite → tested backend formulas → six working browser views and scoped exports. Overview, run details and the remaining views all use one measurement module.
- Synthetic arithmetic/negative/cache/retrieval/failed/unknown/duplicate/no-op fixtures, labeled separately from real local events.

### Local dashboard increments still needed

1. Durable diagnostic counters for event drops/errors across restart; separate event-writer queue with explicit backpressure and aggregation caches for high-volume use. Current synchronous bounded writes and in-process counters are documented and measured.
2. Attach per-agent process/resource and reference-store health feeds. Current health reports dashboard process CPU/peak RSS and scoped event/engine timing; detached stores, throughput windows, current agent RSS and queue lag are unavailable. Windows resource sampling is unavailable.
3. Relative regression alerts over matched cohorts with uncertainty/minimum samples. Current advisory thresholds cover cost/success, task quality, latency, retries, retrieval/validation failures and coverage; no automatic policy mutation exists.
4. Safe metadata backup/restore and physical database compaction; current cohort retention and CSV/JSON/HTML exports work. No forensic secure erasure or raw backup is claimed.
5. Full ancestor/child trace visualization and automatic host request-count/span wiring. Current stable event/run/request/revision IDs and optional caller span/parent IDs are retained and shown as trace details, not a distributed tracing product.
6. Opt-in authorized original/diff UI (if needed). No raw prompt logging was added to build the dashboard. Current original retrieval is through host-scoped SDK/CLI/MCP.

## Phase 2 — implemented interfaces, validation gate open

- Non-streaming Responses adapter implemented and mock tested; live wire compatibility remains untested without authorized credentials.
- MCP minimal stdio server implemented and subprocess tested; owner interactive host installation remains.
- Updated v2 skill and skill-only Codex plugin validated; marketplace/host installation not performed.
- Build artifacts and clean wheel installation tested locally; Windows/Linux/older Python CI jobs configured but not executed here.
- **Next development task:** implement the spend-capped, matched live evaluation runner for the repetitive coding-log workload. Show exact scope/settings/estimated spend; require explicit owner approval and cap; reserve conservative call budgets, record complete provider/cache usage, independent outcomes, retries/retrievals, and paired sample variation. No paid trial has run.

## Phase 3 — compatibility and pilot evidence

Additional providers, TypeScript SDK, verified supported host hooks, streaming/signature-safe handling, optional reviewed semantic rewriting measured separately, and pilot-user evaluations. No transparent interception or arbitrary semantic equivalence claim. Extend precise test-output grammars and downstream tools only with owned adapters and invariant tests. Large subprocess output and process-tree timeout handling need an explicit host execution adapter.

## Phase 4 — only after evidence of value

Free local engine/SDK/CLI/dashboard/basic reports remain in the public core. Optional paid hosted team policies, budgets, administration, integrations and support are hypotheses. Enterprise self-hosting/support later. Use aggregate local metrics with no required raw prompt upload. Hosted multi-tenancy/billing are not implemented, and no money has been spent on services. Pricing, willingness to pay, trademark/package availability and Apache-2.0 ownership review remain validation work; open source permits others' commercial reuse and does not provide exclusivity.
