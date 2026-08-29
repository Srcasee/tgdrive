# Stage 1 — Architecture Convergence

## Objective

Establish a secure application boundary before expanding media/plugin features.

## Video decision

Video streaming remains a Core capability during Stage 1 and is intentionally frozen.

This does **not** create a significant migration penalty because `VideoStreamService` already provides a service boundary between the HTTP file API and Telegram download/cache mechanics. We will not introduce a speculative `MediaPlugin` abstraction yet. When Media Plugin becomes the final architecture phase, the existing service can be wrapped behind a stable media interface without forcing Telegram, authentication or admin domains to depend on the concrete implementation.

Rule: do not add new media implementations to Core during Stage 1.

## Workstreams

### 1. Authentication

The Web application has its own users and sessions. Telegram sessions are infrastructure credentials and are never Web login credentials.

Current implementation:
- `users` table with `user`/`admin` roles.
- PBKDF2-SHA256 password hashes.
- HMAC-signed, expiring Web session token in an HttpOnly cookie.
- `/auth/login`, `/auth/me`, `/auth/logout`.
- `AUTH_SECRET`, `AUTH_TOKEN_TTL`, `AUTH_COOKIE_SECURE` configuration.
- Optional first-admin bootstrap through `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

### 2. Authorization

Minimum roles:

- `user`: browse/search and access files according to product policy.
- `admin`: all user capabilities plus account/source/category administration.

All protected endpoints use explicit FastAPI dependencies (`require_user` / `require_admin`).

### 3. Categories

Categories are now a first-class administrative API:

```text
CategoryRepository
      |
Admin API
      |
Admin UI
      |
files.category_id
```

Implemented endpoints:

- `GET /api/admin/categories`
- `POST /api/admin/categories`
- `PUT /api/admin/categories/{id}`
- `DELETE /api/admin/categories/{id}`
- `PUT /api/admin/files/{file_id}/category`

### 4. Credential boundary

Telegram API ID/hash and session files remain server-side infrastructure credentials. Account APIs return only safe account metadata; raw Telegram session values are not returned.

### 5. File authorization

File listing, search, download, HEAD and stream are protected by Web authentication. Download and stream both reject unavailable files.

### 6. Telegram administration

Account listing, dialog inspection and source creation require admin authorization. Source creation validates the account and the database now enforces `(account_id, telegram_chat_id)` uniqueness.

## Current implementation in this stage

- Added `app/auth/` domain and security primitives.
- Added `users` schema migration.
- Added Web login/logout/me.
- Added live-user authorization dependencies.
- Protected file and Telegram admin APIs.
- Removed Telegram `session` from account list responses.
- Added category repository/API and basic Web category management.
- Added authentication unit tests.
- Added source account validation and uniqueness enforcement.

## Remaining Stage 1 hardening

1. Add integration tests for 401/403 on every protected route.
2. Add category assignment/list filtering tests.
3. Harden full-sync reconciliation semantics before production use.
4. Harden scanner failure state transitions.
5. Complete HTTP Range edge-case handling.
6. Run and fix the complete CI suite.

## Architectural constraint

Core business code must not import concrete Proxy or Media plugins. Proxy is an optional infrastructure capability behind its existing interface. Media Plugin extraction is deferred until the final architecture phase.
