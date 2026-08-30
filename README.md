# tgdrive

Telegram-only file catalog and delivery system.

```text
Telegram
   ↓ metadata-only scan
Ingestion / recognition
   ↓
Resource
   ↓
Catalog / classification / search
   ↓
Delivery
   ↓
Telegram backing locations (with safe pre-transfer failover)
```

Telegram is the only content backend. Multiple Telegram accounts are access/redundancy paths, not storage-provider backends.

## Quick start

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
cp .env.example .env
# set TG_API_ID, TG_API_HASH, TG_PHONE, AUTH_SECRET
docker compose up -d --build
docker compose exec telegram-drive python -m telegram.login
```

Then open `http://<server>:8080/` and configure the Telegram chat/source to scan.

Scanning is metadata-only: a large file is not downloaded to the server just because it is indexed.

See `docs/QUICKSTART.md` for the full operator procedure.

## Optional proxy

Direct Telegram connectivity is the default. Proxy is an external plugin and should only be enabled when the deployment/network requires it.

```bash
docker compose --profile proxy up -d --build
```

The Core application does not contain country/region detection or concrete proxy protocol logic. Proxy configuration is deployment-controlled; changing it requires rebuilding/reconnecting Telegram clients.

## Optional Video capability

Video chunk caching is a plugin, not a Core dependency. Core cataloging, scanning and delivery work without it.

## Development

```bash
cp .env.example .env
docker compose up -d --build
pytest -q
```

## Current status

- Telegram-only architecture: established.
- Logical Resource model: implemented.
- Metadata-only Ingestion/recognition boundary: implemented; scanner orchestration can be further separated.
- Resource-level Catalog and classification: implemented.
- Multi-account backing locations and pre-transfer failover: implemented.
- Web authentication: implemented and isolated.
- Proxy plugin boundary: implemented; explicit reconnect lifecycle remains to be completed.
- Admin Telegram account lifecycle: incomplete.
- Transport optimization: intentionally deferred until multi-path delivery can be measured.

See `docs/ARCHITECTURE.md` and `docs/MIGRATION.md` for the authoritative architecture and migration status.
