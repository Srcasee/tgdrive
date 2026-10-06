# tgdrive Admin Frontend

This frontend is a tgdrive-adapted admin console based on the SnowAdmin ecosystem (Vue 3 + TypeScript + Vite + Pinia + Arco Design). SnowAdmin is MIT licensed; see LICENSE and docs/ADMIN-FRONTEND.md.

The UI intentionally uses tgdrive's existing session-cookie authentication and backend API paths. It does not introduce JWT or a parallel auth service.

## Development
pnpm install
pnpm dev

By default Vite proxies API requests to http://127.0.0.1:8080.

## Production
pnpm build

The generated dist/ directory is copied into the Core image and served by FastAPI under /admin.
