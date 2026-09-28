# Verified primary sources

Checked during implementation on 2026-09-15 UTC (2026-09-14 America/Chicago). Dependency pins reflect packages actually installed from the public Python index; see constraints and installed distribution metadata.

- [Python documentation](https://docs.python.org/3/): pathlib, sqlite3, subprocess argv execution, http.server and standard library contracts.
- [tiktoken official repository](https://github.com/openai/tiktoken) and [package metadata](https://pypi.org/pypi/tiktoken/json): encoding API and MIT license. Adapter around tiktoken, not an original tokenizer algorithm.
- [pytest official guide](https://docs.pytest.org/en/stable/getting-started.html) and [package metadata](https://pypi.org/pypi/pytest/json): pytest CLI, compatibility and dependency pin.
- [Hypothesis official quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html): property test strategy interfaces and pinned release documentation.
- [Responses function calling](https://developers.openai.com/api/docs/guides/function-calling): top-level function definitions, function_call output, function_call_output input, exact call_id and output history handling.
- [MCP lifecycle 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle), [transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools): minimal stdio implementation. This does not imply full protocol conformance.
- [Official skill guide](https://learn.chatgpt.com/docs/build-skills): SKILL.md name/description frontmatter and progressive detail. The environment's bundled OpenAI skill-creator validator was also run.
- [Official plugins repository](https://github.com/openai/plugins), [official plugin manifest sample](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/references/plugin-json-spec.md): skill-only packaging. Environment-bundled OpenAI plugin-creator scaffold and schema validator were read/run. No host-hook is implemented or represented as supported.
- [Apache-2.0 license text](https://www.apache.org/licenses/LICENSE-2.0.txt): exact proposed core license included. Owner/legal publication review remains.

No comparative upstream implementation or competitor source was copied. There are no current commercial price claims to verify: bundled prices are synthetic; real pricing must be configured and versioned by the host.

Additional portability/tooling checks: [Python zoneinfo](https://docs.python.org/3/library/zoneinfo.html) documents the optional tzdata fallback (notably needed on Windows), pinned as `tzdata==2026.4` in the optional dashboard extra; [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) supports the validator-only `PyYAML==6.0.3` dependency. CI uses exact checked release tags [actions/checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) and [actions/setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0); these workflows have not run in this session.
