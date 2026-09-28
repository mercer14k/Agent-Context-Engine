# Honest compatibility matrix · v0.1.0

| Surface | Implemented | Exercised in this session | Remaining |
|---|---|---|---|
| Python core | Python >=3.11, standard library | CPython 3.14.7 | 3.11–3.13 execution in CI |
| macOS Apple Silicon | CPU-only | macOS 26.6.2 arm64 | Intel Mac |
| Windows | pathlib/argv, OS display quoting; documented PowerShell setup | Windows expansion branch under macOS | Actual Windows install/execution, ACL validation |
| Linux | pathlib/argv, POSIX quoting | Linux expansion branch under macOS | Actual Linux installation/execution |
| Offline CLI/SDK | Implemented | Diagnostics, optimize, prepare, registry, expansion, mock loop, benchmark, reports | Pilot workflows |
| Tokenizer | tiktoken 0.14.0 / cl100k_base | Download integrity and cached counts | Other tokenizers/provider mappings |
| Browser dashboard | Bundled static assets + Python stdlib server | Chromium 151 desktop/mobile viewport, HTTP API auth/filter/export checks | Safari/Firefox/Edge and assistive-technology audit |
| MCP | Minimal stdio 2025-11-25 own tools | In-process lifecycle and actual subprocess protocol test | Interactive owner host installation; broader conformance suite |
| Responses | Configurable non-streaming wire adapter | Offline transport/loop contract tests | Owner-approved live provider run and spend-capped paired trial |
| Skill / Codex plugin | v2 skill; supported skill-only manifest | Bundled official validators | Owner host discovery/install test |
| Streaming / semantic rewriting / transparent proxy | Unsupported | Protected passthrough tests | Phase 3 |
| Cloud / paid teams / billing | Not implemented | No services provisioned | Phase 4 evidence gate |

No dependency or integration is advertised as an original trained model. Platform branches are not equivalent to OS-level testing. GPU use is not required; the test browser may use normal platform compositing, but dashboard functionality depends only on standard DOM/SVG.
