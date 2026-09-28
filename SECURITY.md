# Security

This is an unpublished local developer preview. Do not treat argv execution as a sandbox or expose the dashboard on a public interface. Read `docs/ARCHITECTURE.md` for the exact trust model and implemented boundaries.

Use isolated customer workspaces and a trusted host-created Access capability. Keep registry/configuration files outside model write authority. Host approvals must remain out of model arguments. Raw content is memory-only by default; opt-in persistent originals are plaintext, with expiration and size limits, not encryption. Metric task labels must be non-sensitive identifiers. No generic secret detector exists.

Dashboard sessions are loopback-only, HttpOnly/SameSite=Strict and expiring. Origin/Host checks and backend workspace authorization are enforced. No command execution endpoint or raw diff endpoint is exposed. Do not put dashboard login secrets or provider keys in URLs, issue reports, screenshots, exports, or repository files.

Before public release, the owner must establish a private vulnerability-reporting channel and review dependency notices and the proposed license. No reporting address or public repository URL has been invented. Until then, report findings privately to the project owner through an existing trusted channel, with synthetic reproduction data.

Known limits include same-user local access, trusted Python callers, post-validation filesystem races without host isolation, logical rather than forensic data deletion, in-process rather than durable event-loss counters, and unbounded subprocess stdout capture. See the versioned roadmap.
