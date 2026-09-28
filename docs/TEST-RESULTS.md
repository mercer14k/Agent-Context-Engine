# Executed test evidence · rechecked 2026-09-26

## Environment actually exercised

- macOS **26.6.2**, Darwin 25.6.0, **arm64 (Apple Silicon)**.
- CPython **3.14.7**, Clang 21.0.0.
- pytest **9.1.1**, Hypothesis **6.168.0**, mypy **2.3.1**.
- tiktoken **0.14.0**, SHA-256-verified cached **cl100k_base** vocabulary.
- Playwright **1.62.0**, Chromium **151.0.7922.34**.
- CPU-only engine, no model key/provider requests/GPU compute requirement. Browser uses ordinary platform rendering; no GPU dependency is introduced by the app.

## Final executed commands and results

From the repository root (the local browser cache was downloaded explicitly):

```sh
ACE_BROWSER_TESTS=1 PLAYWRIGHT_BROWSERS_PATH="$PWD/.browser-cache" .venv/bin/python -m pytest -q --junitxml=reports/test-results.xml
.venv/bin/python -m mypy src/agent_context_engine
```

**93 passed, zero failures, zero skipped, in 6.26 seconds.** Type checking: **no issues in 19 source files**. Machine-readable evidence: `reports/test-results.xml`.

Coverage includes deterministic argv and approval-denied/no-retry behavior; two deliberate repeated executions of a disposable test; POSIX/Windows display branches; spaces/Unicode paths; unknown/stale registry; protected content; explicit exit status preservation; 100-example JSON properties and 100-example log round trips; numeric lexemes/duplicate keys/nulls; errors among routine logs; exact inventory and hero/chapter/node relationships; store integrity/access/expiry/size/concurrency; stale sources/references; prompt-injection trust tags; absent tokenizer/no-op/budget/overhead; duplicate/cumulative/out-of-order/conflicting usage; zero denominators and missing prices; cache reads/reasoning accounting; retries/evaluation spend/failures/unknown outcomes; concurrent-span wall time; cohort filters; workspace isolation; persistent retention; CSV/HTML escaping; and separation of demo prices from real configuration.

API/browser checks covered unauthenticated access, exact Host/Origin restrictions, authorization, readonly trace endpoints, SDK/API/export agreement, settings, real empty state, permanent demo label, shared filters, 25% workflow arithmetic, separately scoped 40% payload, run drill-down, six views, CSV download, search empty state, responsive 390 px viewport, and keyboard focus. **No JavaScript page errors or unexpected console errors.** One initial unauthenticated 401 console message is expected and separately recorded. This is not a complete accessibility or multi-browser audit.

- `reports/browser/overview-desktop.png`
- `reports/browser/overview-mobile.png`
- `reports/browser/browser-result.json`
- `reports/browser/scoped-demo.csv` (labeled synthetic, filtered to the arithmetic fixture)

## Installation and packaging (clean installation rechecked 2026-09-27)

A wheel was built with `pip wheel --no-build-isolation --no-deps --wheel-dir dist .`. It was installed into a **fresh temporary virtual environment with --no-index --no-deps**. The installed package ran diagnostics, the offline inventory loop, demo seeding, and the arithmetic report successfully. The clean environment had no tokenizer: the documented fallback worked. Web assets, migration and command schema were present inside the wheel. The updated README was also verified inside the wheel on 2026-09-27. See `reports/installation.json`.

The environment-bundled OpenAI skill-creator and plugin-creator validators were run with PyYAML installed. Results: **Skill is valid** and **Plugin validation passed**. Neither an installed host plugin nor a marketplace entry was modified. This verifies package format, not owner-host installation.

The SDK example, exact-context CLI, registry/dry-run generation, offline agent, three-arm benchmark, synthetic report and local instrumentation profile were also exercised. Generated commands execute no live customer mutations. The only executed test mutations were in disposable synthetic workspaces.

## Benchmark evidence (2026-09-15)

`ace benchmark --repeats 5`: **60/60 deterministic fidelity checks passed**, across four fixtures × three arms × five repetitions. No live model outcome or API usage is inferred. Full records and timing variation: `reports/offline-benchmark.json` and `.html`. See `docs/BENCHMARK-RESULTS.md` for the concise result table and methodology link.

## Resource observations

`python benchmarks/profile_local.py`: 500 transforms per condition, five alternating blocks, instrumentation on/off, same synthetic inventory and tokenizer, Python allocation tracing enabled. Median uninstrumented **2.9524 ms**, instrumented **3.1011 ms**, observed increment **0.1487 ms**, zero event drops. These values are local microbenchmark observations, not a service-level target or live task slowdown guarantee. CPU time and Python peak allocation by block are in `reports/local-performance.json`.

One Chromium scripted-flow resource observation: initial login/demo flow **0.2328 s**; renderer task CPU duration after initial load **0.0985 s**; full scripted-flow renderer task CPU **0.2716 s**; JS heap after load **3,199,352 bytes**, increment over blank **2,667,396 bytes**. Source: browser-result.json. These counters cover page task time/JS heap, not all browser processes, OS RSS, long idle sessions or full system CPU. No hardware-cost saving is claimed.

## Local connection recovery (2026-09-26)

Ports 8765 and 8766 belonged to another project’s Python file servers, not the engine dashboard. Port 8765 returned an empty response. Started the engine dashboard in Terminal for workspace `first-test` at `http://127.0.0.1:8767/`: HTTP 200 for the page, HTTP 401 for the API before login. Keep that Terminal window open; use its printed login secret. No other project process was stopped.

The current environment also passed `pip check`; the existing wheel matches all current source and asset files. No source code changes were needed for this recheck.

## Not exercised

Actual Windows/Linux installs, Intel macOS, Python 3.11–3.13, Safari/Firefox/Edge, assistive technology, interactive owner MCP/plugin host, live Responses provider, paid trials, cloud infrastructure, streaming, other providers and semantic rewriting. CI matrices are configured but **were not run here**. No production-readiness or launch-savings claim is supported by these local tests.
