# Stage 1 — Architecture Convergence

## Status

**Phase 1 is complete.** The Core business path is now authenticated, authorized, administrable and covered by the full CI test suite.

## Completed scope

- Web users and roles (`user` / `admin`)
- PBKDF2-SHA256 password hashing
- HMAC-signed, expiring HttpOnly Web sessions
- `/auth/login`, `/auth/me`, `/auth/logout`
- Explicit `require_user` / `require_admin` authorization dependencies
- Protected file list/search/download/HEAD/stream endpoints
- Protected Telegram account/source administration
- Telegram session credentials removed from account API responses
- Category repository, CRUD API, admin UI and file assignment
- Source account validation and `(account_id, telegram_chat_id)` uniqueness
- Full-sync reconciliation semantics hardened
- Scanner failure state transitions hardened
- HTTP Range parsing and 416 handling hardened
- Integration coverage for auth/admin/category/file permissions
- Full CI suite (`pytest -q`) passing

## Video decision

Video streaming remains a Core capability during Stage 1 and is intentionally frozen.

`VideoStreamService` already provides a service boundary between the HTTP file API and Telegram download/cache mechanics. This is sufficient to defer speculative `MediaPlugin` extraction without creating a significant migration penalty.

When Media Plugin becomes the final architecture phase, the existing service can be wrapped behind a stable media interface without forcing authentication, admin, file or Telegram domains to depend on concrete media implementations.

**Rule:** do not add new media implementations to Core before the Media Plugin phase.

## Download performance boundary

The public download and video-stream APIs are not the content-source bottleneck themselves. Both ultimately depend on `TelegramDownloader.stream()`, which calls Telethon `iter_download()` against Telegram.

The important layers are:

```text
Browser
  -> FastAPI file/stream endpoint
  -> TelegramDownloader.stream()
  -> Telethon iter_download()
  -> Telegram DC / network / proxy
```

Video playback additionally has `VideoStreamService` and a 4 MiB application cache chunk. Normal downloads currently stream directly from Telegram and do not use the video cache.

Before Phase 2, download performance should be benchmarked and optimized at the Telegram transport boundary rather than coupling performance work to future Media Plugins. The optimization must preserve the Core interface so proxy selection can remain an independent plugin concern.

## Phase 2 boundary

Phase 2 starts only after the Core path above is stable. It focuses on infrastructure extensibility, especially account-scoped proxy selection and controlled proxy lifecycle/reload. Media Plugin extraction remains a later phase.

## Architectural constraint

Core business code must not import concrete Proxy or Media plugins. Optional infrastructure capabilities may implement stable Core interfaces, but Core must remain usable without any optional plugin installed.
