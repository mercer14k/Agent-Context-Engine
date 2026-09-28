# Local benchmark results · v0.1.0

Five repeats per arm, identical synthetic fixtures, balanced/shuffled order (seed 217), tiktoken 0.14.0 `cl100k_base`. Counts cover the complete inner tool-result envelope (role, trust, content, optional reference). They exclude a full agent conversation/provider framing. No model, paid call, provider cache or live output generation occurred.

| Workload | Engine off tokens | Concise native tokens | Engine tokens | Extra benefit vs native | Deterministic fidelity |
|---|---:|---:|---:|---:|---:|
| Repetitive coding log with embedded error | 3,362 | 3,362 | 143 | 3,219 fewer | 15/15 |
| Exact 40-row inventory | 2,314 | 1,663 | 1,663 | 0 | 15/15 |
| Already-scoped agent handoff | 530 | 369 | 369 | 0 | 15/15 |
| Already compact JSON | 19 | 19 | 19 | 0; bypass | 15/15 |

The log encoding reconstructs exact text and preserves the error. The inventory produces exactly 4,200 units, a Decimal valuation of 518.518513851851851384200, and no mismatches. The handoff keeps the distinct 10-hero / 12-chapter / 12-nodes-per-chapter requirements and dependency relationship. These are transform/outcome fixture assertions, not live model-quality evidence.

Median engine processing/replay wall time in the recorded benchmark: coding log **1.036 ms**, inventory **1.534 ms**, handoff **0.447 ms**, no-op **0.128 ms**. Corresponding concise native median: **0.974**, **0.897**, **0.323**, **0.123 ms**. Engine processing is additional work; matching native token counts is not a savings win. Full min/max variation, each record, hashes, environment and configuration are in the report.

A separate current-host `run_tests` interface comparison counted definitions, visible defaults, instructions and one expected generated call: **276 compact-interface tokens versus 217 native-interface tokens**. It selected the native interface because the compact dictionary/schema did not amortize over a single call. Executable/working-directory path lengths affect these numbers. `reports/command-comparison.json` records the scope; regenerate with the included example for your own host. No execution or model call is needed to expand a validated request.

## Synthetic acceptance, kept separate

The 12,000 → 9,000 workflow demonstration yields **25%** reduction; the separately scoped 10,000 → 6,000 main input boundary yields **40%**. An additional retrieval-context request accounts for 1,000 input tokens exactly once. Other demonstration cases include negative savings, cost regression after lost cache benefit, a failed task, missing usage and duplicate events. **None of these synthetic counts are product savings claims.**

## Conclusions supported by the measurements

Adjacent repeated logs are the strongest candidate for further evaluation. JSON already minified by a capable native tool offers no additional payload reduction here. Compact-command overhead can exceed its benefit. Full workflow token reduction, provider-reported cost, cost per successful live task and agent-quality/latency effects remain **unavailable** until a controlled live evaluation runs.

**Next development task:** implement a spend-capped paired live evaluation runner for the repetitive-log workload, with retrieval follow-ups, concise native baseline, full provider/cache usage and independent task validation. Require explicit owner approval and a spending limit before running it.

See `docs/MEASUREMENT.md` for exact formulas, normalization rules, cohort matching, limitations and the evidence gate. No competitor baseline was incorporated or published. No model output savings, universal compatibility or percentage launch promise is asserted.
