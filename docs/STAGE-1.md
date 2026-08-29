# Stage 1 — Architecture Convergence

## Objective

Establish a secure application boundary before expanding media/plugin features.

## Workstreams

### 1. Authentication

Introduce an `app.auth` domain boundary containing an authenticated `Principal` and authorization policy. Transport-specific authentication (session/JWT/etc.) must be selected and implemented as a separate adapter; Telegram sessions are not web credentials.

### 2. Authorization

Minimum roles:

- `user`: browse/search and access files according to product policy.
- `admin`: all user capabilities plus account/source/category administration.

All admin endpoints must pass an explicit admin policy check.

### 3. Categories

Expose categories as a first-class domain:

```text
CategoryRepository
      |
CategoryService
      |
Admin API
      |
Admin UI
      |
files.category_id
```

### 4. Credential boundary

Telegram API ID/hash and session files remain server-side infrastructure credentials. They must never be returned by normal web APIs. Account responses should contain safe metadata only.

### 5. File authorization

Download and streaming must use the same authorization and availability policy. A deleted/unavailable file must not become readable merely because a stream endpoint is used.

## Current implementation in this stage

- Added `app/auth/` as the application-level authentication/authorization boundary.
- Added `Principal` and an explicit `require_admin` policy.
- Documented the target boundary without coupling it to a specific authentication transport yet.

## Next implementation steps

1. Choose the web credential mechanism and implement the authentication adapter.
2. Add user/admin persistence and bootstrap strategy.
3. Wire auth dependencies into FastAPI routes.
4. Remove session fields from public account responses.
5. Implement category repository/service/API and admin UI.
6. Add integration tests for 401/403 and protected downloads/streams.
7. Run the complete CI suite before beginning media-plugin refactoring.

## Architectural constraint

Do not add more concrete media implementations to `files/api.py` while Stage 1 is in progress. Media plugin extraction belongs after the security/admin boundary is stable.
