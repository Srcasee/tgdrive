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

The Core image contains the application code. Runtime data is persisted under `./data`. The normal service mounts only `plugins/proxy` as an optional plugin; the Video plugin is not part of the Core runtime.

## Normal bootstrap

1. Copy `.env.example` to `.env`.
2. Set `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`, `AUTH_SECRET`, and the Web admin credentials.
3. Start Core and PostgreSQL:

```bash
docker compose up -d --build
```

4. Complete Telegram login for an explicit account name:

```bash
./login-account.sh default +1234567890
```

5. Open the Web UI on port `8080` and configure the exact Telegram chat/source to scan.

No manual PostgreSQL SQL or manual account-row creation is required for the normal bootstrap.

## Data and storage rules

- PostgreSQL stores metadata, Resource identity, categories, source state and account metadata.
- Telegram remains the source of file bytes.
- Scanner/Ingestion is metadata-only and must not download a complete file merely to index it.
- Telegram session files are persisted under `/data/accounts/<account_name>` by default.
- The physical `files` table represents Telegram-backed locations; it is not a public File API.

## Web UI

The active UI is a dependency-free Resource-first browser client. It uses `/catalog`, `/catalog/search`, `/resources/{id}/download`, `/resources/{id}/share`, and Resource-level admin classification endpoints.

There are no compatibility `/files/*` HTTP routes.

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

Core does not perform country/region detection and does not contain concrete proxy protocol logic.

Changing proxy configuration currently requires recreating/restarting Telegram clients; plugin registry refresh alone does not mutate existing Telethon clients. This remains tracked in Issue #20.

## Video

Video playback/chunk caching is outside the current real-device test plan. The optional plugin is not loaded by the normal Core runtime and must remain independent of cataloging, scanning, Resource identity and ordinary download delivery.

## Current operational verification

The automated CI suite validates the PostgreSQL-backed application. Real Telegram connectivity and proxy smoke tests are deployment-level checks and should be run on the target server.

The current real-device sequence is intentionally staged:

```text
1. Core + PostgreSQL health
2. Telegram direct connectivity
3. Telegram login/session reuse
4. Source configuration
5. Metadata-only scan
6. Resource/Catalog search + classification
7. Single-source delivery
8. Multi-account Resource failover
9. Range/stream verification
10. Optional proxy connectivity when required
```

Video is intentionally excluded.

## Known operational gaps

- Telegram account admin lifecycle and health (Issue #18).
- Proxy client reconnect/rebuild semantics (Issue #20).
- Delivery source health/ranking and retry policy (Issue #19).
- Transport optimization after multi-path measurements (Issue #21).
- Top-level `telegram` Python package namespace remains a packaging concern (Issue #22).
- Canonical SHA-256 Resource promotion after complete verification (Issue #24).
