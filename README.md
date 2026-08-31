# tgdrive

Telegram-only file catalog and delivery system.

```text
Telegram metadata
      ↓
Recognition / Ingestion
      ↓
Logical Resource
      ↓
Catalog / classification / search
      ↓
Resource delivery
      ↓
Telegram backing locations
```

Telegram is the only content backend. Multiple Telegram accounts are access/redundancy paths, not storage-provider backends.

## Quick start

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
cp .env.example .env
# set TG_API_ID, TG_API_HASH, TG_PHONE, AUTH_SECRET
docker compose up -d --build
./login-account.sh default +1234567890
```

Then open `http://<server>:8080/` and log in with the configured Web user. Configure the Telegram source through the Telegram management API/UI.

`login-account.sh` is only a deployment wrapper around the canonical `app/telegram/login.py` implementation. Account-named sessions are stored under `/data/accounts/<account_name>`. Multiple Telegram accounts/sessions are supported.

Scanning is metadata-only: a large Telegram file is not downloaded to the server merely because it is indexed.

See `docs/QUICKSTART.md` for the operator procedure.

## Core API

The active HTTP API is Resource-first:

```text
GET  /catalog
GET  /catalog/search?q=...
GET  /catalog/{resource_id}
GET  /resources/{resource_id}/download
HEAD /resources/{resource_id}/download
GET  /resources/{resource_id}/stream
HEAD /resources/{resource_id}/stream
POST /resources/{resource_id}/share
```

Categories are attached to logical Resources through the admin API:

```text
GET  /api/admin/categories
POST /api/admin/categories
PUT  /api/admin/categories/{category_id}
DELETE /api/admin/categories/{category_id}
PUT  /api/admin/resources/{resource_id}/categories
```

Telegram account lifecycle is explicit:

```text
GET  /api/telegram/accounts
PUT  /api/telegram/accounts/{account_id}/enabled
POST /api/telegram/reconnect
GET  /api/telegram/accounts/{account_id}/dialogs
POST /api/telegram/sources
```

There are no compatibility `/files/*` HTTP endpoints. Physical Telegram locations are persistence details behind the Resource model.

A complete non-range delivery hashes the emitted content with SHA-256 and promotes the consumed physical location to its canonical Resource identity.

## Optional proxy

Direct Telegram connectivity is the default. Proxy is an external plugin and should only be enabled when the deployment/network requires it.

```bash
docker compose --profile proxy up -d --build
```

The Core application does not contain country/region detection or concrete proxy protocol logic. Proxy configuration is deployment-controlled. After changing proxy settings, use the administrator reconnect endpoint or restart the service so Telegram clients are rebuilt.

## Video

Video chunk caching is intentionally outside the current real-device testing scope. The optional Video plugin is not a Core dependency, is not mounted by the normal Compose service, and must not influence cataloging, scanning, Resource identity, or ordinary download delivery.

## Development

```bash
cp .env.example .env
docker compose up -d --build
pytest -q
```

## Current status

- Telegram-only Resource architecture: established.
- Metadata-only recognition/Ingestion: implemented.
- Logical Resource + physical Telegram backing locations: implemented.
- Resource catalog, search and Resource-level classification: implemented.
- Multi-account Telegram backing paths and pre-transfer failover: implemented.
- Account enable/disable and runtime scanner reconciliation: implemented.
- Resource-first Web UI: implemented for catalog/search/download/share and basic admin classification.
- Legacy File-centric HTTP/admin paths: removed.
- Complete non-range delivery verification and canonical Resource promotion: implemented.
- Proxy boundary and explicit client reconnect: implemented.
- Transport optimization and richer source scheduling: deferred until real-device measurements justify them.

See `docs/ARCHITECTURE.md`, `docs/PROJECT-STATUS.md`, and `docs/MIGRATION.md` for the current architecture and status.
