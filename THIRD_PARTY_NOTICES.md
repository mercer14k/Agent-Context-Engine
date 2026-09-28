# Third-party dependency and license inventory

The core implementation is original. No Headroom, RTK, competitor source or model weights were incorporated. The tokenizer is an adapter around OpenAI tiktoken, not an original tokenization algorithm. No third-party implementation was modified.

Dependencies are installed separately from their original distributions; their source/wheels are not bundled in the repository archive. Versions were selected from official package metadata/documentation and pinned in pyproject.toml and constraints.txt. The table includes runtime extras, development/browser tools and installer/build dependencies present in the tested environment. The standard-library core has no external runtime requirement. The conditional Windows pytest dependency colorama is pinned and its actual wheel license verified; CI on Windows has not run.

Upstream license/notice files were copied verbatim from the installed distributions, preserving their internal directory paths, under third_party_licenses/. Their exact paths and dependency relations are in docs/dependency-metadata.json. This inventory records actual distributed licenses; it is not a legal assurance about the complete future distribution. Review before publication.

| Distribution | Pinned version | Distributed license | Notice files |
|---|---|---|---|
| ast_serialize | 0.11.2 | MIT | 2 |
| certifi | 2026.7.22 | MPL-2.0 | 1 |
| charset-normalizer | 3.5.1 | MIT | 1 |
| greenlet | 3.5.6 | MIT AND PSF-2.0 | 2 |
| hypothesis | 6.168.0 | MPL-2.0 | 1 |
| idna | 3.19 | BSD-3-Clause | 1 |
| iniconfig | 2.3.0 | MIT | 1 |
| librt | 0.15.0 | MIT | 1 |
| mypy | 2.3.1 | MIT | 2 |
| mypy_extensions | 1.1.0 | MIT | 1 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | 3 |
| pathspec | 1.1.1 | MPL-2.0 | 1 |
| pip | 26.2.1 | MIT | 22 |
| playwright | 1.62.0 | Apache-2.0 | 1 |
| pluggy | 1.6.0 | MIT | 1 |
| pyee | 13.0.1 | MIT | 1 |
| Pygments | 2.21.0 | BSD-2-Clause | 2 |
| pytest | 9.1.1 | MIT | 1 |
| PyYAML | 6.0.3 | MIT | 1 |
| regex | 2026.9.10 | Apache-2.0 AND CNRI-Python | 1 |
| requests | 2.34.2 | Apache-2.0 | 2 |
| setuptools | 84.0.0 | MIT | 15 |
| sortedcontainers | 2.4.0 | Apache-2.0 | 1 |
| tiktoken | 0.14.0 | MIT | 1 |
| typing_extensions | 4.16.0 | PSF-2.0 | 1 |
| tzdata | 2026.4 | Apache-2.0 | 2 |
| urllib3 | 2.7.0 | MIT | 1 |

The browser downloaded solely for local tests (Chromium/FFmpeg) and the virtual environment are excluded from the repository archive. Browser binary redistribution/licensing is outside this artifact; install through Playwright's documented installer. The downloaded public tokenizer vocabulary is also excluded; it is prepared explicitly by the operator and hash-verified.

The proposed Apache-2.0 license applies to our original public core. It allows commercial reuse by others and does not create exclusivity. Owner/legal review is required before publishing. Future proprietary services must stay separate. No repository, package or plugin was published or installed into the owner's host.

Conditional Windows test dependency: **colorama 0.4.6**, BSD-3-Clause; upstream wheel integrity/notice verified without executing it. See third_party_licenses/colorama/.
