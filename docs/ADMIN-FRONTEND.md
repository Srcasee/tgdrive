# Admin Frontend Integration

## Decision

The legacy static admin UI under app/web/admin.html and app/web/admin/ is retired. The new admin console lives under frontend/ and is served by Core at /admin.

The new console follows the SnowAdmin ecosystem: Vue 3, TypeScript, Vite, Pinia-compatible state architecture and Arco Design. The initial integration intentionally keeps the business layer small and maps directly to tgdrive's existing HTTP API instead of importing SnowAdmin's unrelated demo pages.

SnowAdmin is MIT licensed. A copy of its license is retained at frontend/LICENSE; the project source is credited to imwangfan/SnowAdmin.

## Authentication

The frontend uses the existing tgdrive session-cookie endpoints:
- POST /auth/login
- GET /auth/me
- POST /auth/logout

No JWT or browser-stored session token is introduced. Axios sends credentials with withCredentials=true.

## API mapping

| UI | Backend |
|---|---|
| Login | /auth/login, /auth/me, /auth/logout |
| Resource catalog | GET /catalog, GET /catalog/search, GET /catalog/{id} |
| Categories | /api/admin/categories CRUD |
| Resource classification | PUT /api/admin/resources/{id}/categories (API client ready) |
| Telegram accounts | GET /api/telegram/accounts, enable/disable |
| Telegram dialogs | GET /api/telegram/accounts/{id}/dialogs, delete |
| Telegram sources | list/create/enable/delete under /api/telegram/sources |
| Telegram runtime | POST /api/telegram/reconnect, POST /api/telegram/reconcile |
| Downloads | /api/admin/downloads/active, /history, delete |

Features not backed by an existing API are not faked in the UI.

## Deployment

Docker now builds frontend/ in a Node stage and copies dist/ into the Core image. FastAPI serves that build under /admin.

For local development:

    pnpm --dir frontend install
    pnpm --dir frontend dev

The Vite dev server proxies /auth, /api, /catalog, and /resources to Core on port 8080.

## Follow-up

The current integration is the first real backend/frontend connection. The next UI iteration should add resource detail/classification workflows, share management screens and richer Telegram dialog/source actions after the corresponding API contracts are stabilized.
