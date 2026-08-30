# Deployment Notes

## Deployment contract

The supported deployment is deliberately small:

```text
.env
  |
  v
docker compose up -d --build
  |
  +--> PostgreSQL
  +--> tgdrive Core

Optional only when required by the server/network:
  docker compose --profile proxy up -d --build
```

The Core image contains the application code. The Compose deployment persists only runtime data under `./data` (PostgreSQL data and Telegram session/runtime data); it no longer bind-mounts `./app` over the application installed in the image.

## Normal bootstrap

1. Copy `.env.example` to `.env`.
2. Set `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`, `AUTH_SECRET`, and the admin credentials you want to use.
3. Start Core and PostgreSQL:

```bash
docker compose up -d --build
```

4. Complete Telegram login when required:

```bash
docker compose exec telegram-drive python -m telegram.login
```

5. Open the web UI on port `8080` and configure the exact Telegram chat/source to scan.

No manual PostgreSQL SQL or manual account-row creation is required for the normal single-account bootstrap.

## Data and storage rules

- PostgreSQL stores metadata, Resource identity, categories, source state and account metadata.
- Telegram remains the source of file bytes.
- Scanner/ingestion is metadata-only and must not download a complete file merely to index it.
- Telegram session files are persisted under `/data/accounts` by default.
- Optional Video caching, if enabled, is plugin-owned and is not required by Core.

## Proxy deployment

Proxy is an external plugin under `plugins/proxy/` and is not a Core storage/domain dependency.

Default:

```env
TG_PROXY_ENABLED=false
```

Proxy-enabled deployment:

```env
TG_PROXY_ENABLED=true
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
```

Then:

```bash
docker compose --profile proxy up -d --build
```

The plugin can run a sing-box upstream. Core does not perform country/region detection and does not contain concrete proxy protocol logic.

Changing proxy configuration currently requires recreating/restarting the Telegram clients; plugin registry refresh alone does not mutate existing Telethon clients. This remains tracked in Issue #20.

## Current operational verification

The automated CI suite validates the PostgreSQL-backed application and both supported Python versions. Real Telegram connectivity and proxy smoke tests are deployment-level checks and should be run on the target server before production use.

The next real-server sequence is intentionally staged:

```text
1. Core + PostgreSQL health
2. Telegram direct connectivity
3. Telegram login/session reuse
4. Optional proxy connectivity
5. Source configuration
6. Metadata-only scan
7. Resource/Catalog search + classification
8. Single-source delivery
9. Multi-account Resource failover
10. Range/stream verification
```

## Known operational gaps

- Telegram account admin lifecycle (enable/disable/retire/remove) is not yet a complete management surface (Issue #18).
- Proxy client reconnect/rebuild semantics need an explicit lifecycle operation (Issue #20).
- Delivery source health/ranking and retry policy remain follow-up work (Issue #19).
- Transport optimization remains deferred until multi-path delivery can be measured (Issue #21).
- The top-level `telegram` Python package namespace remains a packaging concern (Issue #22).
