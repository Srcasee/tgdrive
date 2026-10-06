# Security & Reliability Audit Record

> Status: **record only; no remediation in this change set.**

This document records the previous full-repository audit findings. The findings remain intentionally unfixed.

## High

### H-01 — Scanner forces full Telegram scans
- Location: app/telegram/scanner.py
- Current behavior forces sync_mode=full and traverses client.iter_messages(dialog.entity).
- Risk: repeated large-channel enumeration, FloodWait/rate-limit exposure, DB write amplification, long scan cycles and poor fairness between Sources.
- Recommendation: implement real incremental | full | repair modes, persist/use last_message_id, and define deletion/edit/repair semantics.

### H-02 — Production cookie security defaults to insecure transport
- Locations: deploy.sh, app/auth/api.py, docker-compose.yml, deployment docs.
- Current deployment defaults AUTH_COOKIE_SECURE=false while Core is exposed as plain HTTP on port 8080.
- Risk: session credentials can be intercepted if deployed directly without TLS.
- Recommendation: production HTTPS, AUTH_COOKIE_SECURE=true, HSTS and an explicit reverse-proxy/production baseline.

### H-03 — No login rate limiting / brute-force defense
- Location: app/auth/api.py
- Login has credential verification but no IP/account throttling, lockout or backoff.
- Risk: online password guessing.
- Recommendation: dual-dimension rate limiting (IP + account) with progressive backoff.

## Medium

### M-01 — Weak PostgreSQL fallback password
- Locations: docker-compose.yml, app/config.py
- Default/fallback credentials use tgdrive/tgdrive.
- Recommendation: require an explicit production DB password and remove weak fallbacks.

### M-02 — Telegram session files need stronger filesystem hardening
- Locations: data/accounts, Telegram login/session handling.
- Telegram session files are sensitive account credentials.
- Recommendation: 0700 account directories, 0600 session files, non-root runtime, ownership checks and secure backup policy.

### M-03 — Proxy plugin listens on 0.0.0.0:1080 without authentication
- Location: plugins/proxy/plugin.py
- It is not host-published by default, but other network peers may reach it.
- Recommendation: internal-only networking or authentication/network isolation.

### M-04 — PluginRuntime is a trusted Python-code execution boundary
- Location: app/plugins/runtime.py
- Plugin modules are imported and executed in-process.
- Recommendation: document the plugin directory as trusted code; if third-party plugins are ever supported, isolate them behind a process/container/RPC boundary.

### M-05 — Migration drops the download_records.resource_id foreign key
- Location: app/database.py
- Migration removes the FK without replacing it with an explicit lifecycle rule.
- Recommendation: use nullable resource_id with ON DELETE SET NULL, or define an explicit snapshot lifecycle.

### M-06 — Resource/share access is global to authenticated users
- Locations: catalog/download/share APIs.
- Current model does not scope resources/shares to an owner.
- Recommendation: if multi-user tenancy is required later, add owner/ACL/visibility semantics.

### M-07 — Python dependencies are not fully locked
- Location: requirements.txt
- Recommendation: introduce a reproducible lock mechanism plus dependency vulnerability/SBOM checks.

### M-08 — Container hardening is limited
- Locations: Dockerfile, Compose.
- Recommendation: non-root runtime, cap_drop: ALL, no-new-privileges, read-only filesystem where practical and minimal writable mounts.

## Low

### L-01 — Scanner repeatedly enumerates account dialogs
- Location: app/telegram/scanner.py
- Recommendation: cache account → chat/entity lookup.

### L-02 — Dialog discovery currently filters by channel semantics
- Location: app/telegram/dialog_discovery.py
- Recommendation: maintain a test matrix for private/public channels, supergroups, groups, discussion groups and forums.

### L-03 — Session tokens lack server-side revocation/versioning
- Locations: app/auth/security.py, auth model.
- Recommendation: add session version/revocation semantics.

### L-04 — Share tokens have no expiration
- Location: share repository/API.
- Recommendation: optional expiry with permanent links as an explicit choice.

### L-05 — Some admin errors expose raw exception strings
- Recommendation: return safe messages plus server-side correlation IDs.

## Positive controls observed

- SQL access inspected in core paths is parameterized; no obvious SQL injection was found.
- Password hashing uses PBKDF2-HMAC-SHA256 with random salt.
- Session tokens use HMAC-SHA256 and constant-time signature comparison.
- Share tokens use cryptographically strong random values.
- Delivery failover avoids replaying bytes after a response has already emitted data.
- The test suite already covers auth, API integration, failover, content verification, proxy runtime, range behavior and Telegram components.
