# Evidence artifacts

These files record executed local checks and synthetic demonstrations. See ../docs/TEST-RESULTS.md and ../docs/BENCHMARK-RESULTS.md for dates, environments, exact measurement boundaries, and limitations.

- `offline-benchmark.*`: deterministic offline fixture replay; no provider calls.
- `arithmetic-demo.*` and `browser/scoped-demo.csv`: explicitly simulated workflow measurements.
- `browser/`: Chromium acceptance screenshots and recorded browser checks.
- `test-results.xml`: local pytest results; not a hosted CI result.
- `command-comparison.json`: tokenizer-counted interface comparison from the captured local environment.
- `installation.json`: clean wheel-install evidence.
- `local-performance.json`: local instrumentation microbenchmark.

Before repository preparation, the command-comparison artifact contained the author's absolute checkout path. It now uses `<workspace>`; its captured token counts and digests are unchanged and should not be recomputed from that redacted path. The JUnit hostname is replaced with `local-test-host`. No test outcomes or timing values were altered by these redactions.

Re-running examples or tests may replace artifacts. Never commit reports containing real prompts, login secrets, keys, or private data.
