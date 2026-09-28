# Measurement methodology · v1

## Distinct evidence

**Tokenizer-counted payload** counts one result envelope, including role/trust and any reference. The optional tokenizer is pinned tiktoken 0.14.0, `cl100k_base`. This is an explicit encoding; no automatic current model mapping or complete billing equivalence is asserted. Missing tokenizer produces a no-op and null counts, never characters divided by four.

**Provider-reported usage** is normalized once per request across retries, handoffs and retrieval-driven calls. Schema/skill/dictionary text entering a request is already part of reported input and must not be added again. Reasoning tokens remain a diagnostic subset of output. Post-generation shrinking cannot refund generated output. MCP framing and provider role serialization are not part of the payload counter; provider totals are needed to account for them.

**Paired comparison** requires the same workload, provider, model, tokenizer, configuration, pair ID, price version and usage evidence. `off`, `native`, and `engine` arms pair only one-to-one; ambiguous pair groups are not pooled. An optimized-only run receives no observed counterfactual. Mixed token strata produce no pooled token-total claim. Compatible reductions use summed counts, not means of percentages.

`raw_usage` preserves the provider's numeric usage fields. For the Responses custom-function-only adapter, input includes cached-input tokens; cached reads are a subset, cache writes normalize to zero (no separately identified cache-write category used by this adapter), and reasoning is included in output. Other providers must define their own adapter/rules. Do not feed provider fields with overlapping meanings into this normalization.

Prices require provider/model/version, currency, rate source, effective date, input/cache-read/cache-write/output rates per million, a fractional discount and the named normalization rule. No current commercial price is bundled. Demonstration prices are clearly synthetic, supplied only to demo-mode aggregation and never persisted into real workspace pricing. Calculated cost is not an invoice or a flat-rate subscription saving. Billable built-in tool services are unsupported by the Responses adapter; generic events must explicitly report tool-service cost or leave it unknown.

Partial known spend remains a labeled subtotal. Missing costs are never zero. Cost per success includes failed attempts and retries in its numerator, excludes unknown outcomes from the success denominator, and becomes provisional when outcomes are unevaluated. Judge/evaluation spend is separate with an all-in total. Local compute has no invented currency cost.

## Event contract

Stable event IDs deduplicate exact delivery. Stable provider request IDs plus monotonically increasing `revision` replace cumulative snapshots. Only the latest **final** complete snapshot counts as complete usage; contradictory equal revisions are flagged. Every run declares `expected_requests` so missing calls cannot silently disappear. Retries with actual extra provider calls need distinct request IDs; a retry diagnostic does not itself add tokens. Unknown outcomes need null `success`, and a named validator is required to treat a boolean as evaluated.

Runs use task start/end wall time. Concurrent child spans do not add to task duration. Median/p95 are computed over individual durations with sample sizes. Requests may carry `trace_id`, `span_id`, `parent_span_id`, and `task_id`; the SDK caller maintains these relationships. v0.1 does not automatically discover distributed agent ancestry or reconstruct omitted host events.

## Offline replay

`ace benchmark --repeats 5` balances three arms per identical fixture:

- **Engine off**: original payload.
- **Efficient native**: minified JSON where applicable; log text unchanged because no generic summary can safely preserve arbitrary log meaning.
- **Engine on**: configured deterministic transform, complete envelope count and adaptive bypass.

The four workloads are a repeated coding log with an error among routine lines; exact inventory reconciliation (40 rows, 4,200 total units and exact Decimal valuation); an already task-scoped handoff preserving 10 heroes, 12 chapters and 12 nodes per chapter; and an already compact no-op. The handoff benchmark measures envelope serialization, not a claimed semantic summarizer or history scoping win. Registered command interface costs are reported separately because the executable path lengths are environment-dependent.

Order is shuffled reproducibly using seed 217; this controls fixture order only, not model generation. Five repeats per arm yield 60 boundary observations; token counts are deterministic, transform latency varies. Hashes, model absence, tokenizer version, environment, median/min/max latency and each fidelity result are recorded. No provider account, output generation, prompt cache, judge or paid API is involved. Workflow API usage, cost per successful model task, live quality intervals and output-token savings remain unavailable. A competitor configuration is not included; no upstream code is copied.

A zero-exit command and a faithful transform are separate from end-task quality. Offline fidelity events use `transform_fidelity` with unknown task success. The mock inventory agent has an independently checked offline outcome, explicitly labeled as a mock. These must not be presented as live reliability evidence.

## Synthetic acceptance mode

`ace seed-demo` is idempotent and writes only `mode=demo`; all usage/outcomes are labeled Simulated. Live empty mode stays empty. Demonstrations include 25% workflow arithmetic, negative savings, retrieval overhead, a lost-cache cost regression despite fewer tokens, failed quality, missing usage, a no-op, retries, duplicate deliveries and cumulative snapshots. Export names/content carry the mode.

Arithmetic baseline: one request with 10,000 input + 2,000 output. Engine: one request with 6,000 input + 2,000 output, plus a distinct retrieval-context request with **1,000 input and zero output**. Thus 12,000 → 9,000 = 25%. The separate main-payload card is 10,000 → 6,000 = 40%. The overhead is counted once as a request, never added again from optimization events.

## Next evidence gate

The included measured payload results do not authorize a launch claim. The first next task is a matched local agent trial on the repetitive-log workload, including the best concise baseline and retrieval follow-ups. Implement a reviewable trial scope, configured prices, conservative per-request spend reservations and an explicit owner-approved cap before any paid run. Then run balanced paired repetitions and report uncertainty, failures, retries, actual usage, cache effects and cost per independently verified task. The manual Responses example is not a spend-capped evaluation runner.
