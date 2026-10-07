# TGDrive Migration / Architecture Convergence Record

Updated 2026-08-31 after the Resource migration cleanup and Web UI rewrite.

## Product definition

tgdrive is a **Telegram-only** file catalog and delivery system.

```text
Telegram metadata
      ↓
Recognition / Ingestion
      ↓
Logical Resource
      ↓
Catalog + classification + search
      ↓
Download / Range delivery
      ↓
Telegram backing locations
```

Telegram is the only content backend. No generic storage-provider abstraction is planned.

## Converged architecture

```text
Web User
   |
   +--> Catalog --> Resource --> Delivery --> Telegram backing locations
   |       ^                         ^             |
   |       |                         |             +--> TG account A
   |       |                         |             +--> TG account B
   |       |                         |             +--> TG account C
   |       |                         |
   |       +--> Resource categories  +--> source selection / failover
   |
   +--> Auth (cross-cutting)

Telegram backing locations --> Telegram API --> Connectivity --> Direct / Proxy plugin
```

## Migration decisions

### Logical Resource

Implemented. `resources` is the logical business entity; the physical `files` table represents Telegram-backed message locations. Physical identity remains `(account_id, telegram_chat_id, message_id)` and each physical location points to a Resource through `resource_id`.

### Recognition / Ingestion

Implemented. Telegram traversal produces normalized `TelegramFileObservation` records. Ingestion owns recognition/persistence coordination. Scanner still owns some scan orchestration, but no longer represents the public domain model as File records.

### Classification

Implemented at Resource level. Categories are attached through `resource_categories`. The live `files.category_id` column and file-level category API have been removed.

### Delivery

Implemented as Resource-first HTTP delivery. The public contract uses `/resources/{resource_id}/download` and `/resources/{resource_id}/stream`, with Range support and safe pre-transfer Telegram source failover.

### Physical persistence naming

The persistence adapter is named `TelegramFileRepository` to make the boundary explicit: the `files` table is a physical Telegram-location store, not the application's public File domain.

### Web UI

The old File-oriented browser was replaced rather than kept behind compatibility endpoints. The current UI consumes the Resource-first Catalog/Delivery APIs directly and does not depend on Video.

### Video

Video chunk caching remains an optional plugin, outside the Core delivery path and outside the current real-device test scope. Core streaming no longer loads or calls the Video capability. The normal Compose service does not mount the Video plugin.

### Legacy compatibility

Compatibility was intentionally rejected. The active codebase does not retain `/files/*` HTTP routes, the old file-category admin route, or the obsolete FileRepository adapter name.

## Current repository tree

```text
app/
├── admin/
├── auth/
├── catalog/
├── common/
├── core/
├── delivery/
├── ingestion/
├── plugins/
├── repositories/
│   ├── accounts.py
│   ├── categories.py
│   ├── resources.py
│   ├── shares.py
│   ├── sources.py
│   └── telegram_files.py
├── telegram/
├── web/
├── config.py
├── database.py
└── database_pool.py

plugins/
└── proxy/
```

The optional Video plugin may remain separately versioned outside the Core runtime; it is not part of the active architecture or test path.

## Current operational state

Implemented:

- account-named Telegram sessions
- explicit Telegram source configuration
- metadata-only scanning
- logical Resource identity
- physical Telegram backing locations
- Resource catalog/search/classification
- Resource download and Range delivery
- pre-transfer source failover
- Resource-first Web UI
- external Proxy plugin boundary

Tracked follow-up work:

1. Issue #24 — canonical SHA-256 Resource promotion after complete verification.
2. Issue #18 — Telegram account lifecycle and health.
3. Issue #19 — delivery source health/ranking.
4. Issue #20 — proxy reconnect/rebuild lifecycle.
5. Issue #21 — transport optimization after real-device measurements.
6. Issue #22 — top-level `telegram` package namespace concern.

## Deployment direction

Normal deployment:

```bash
docker compose up -d --build
./login-account.sh <account_name> <phone>
```

Optional proxy deployment:

```bash
docker compose --profile proxy up -d --build
```

The Core runtime mounts only the Proxy plugin. Video is deliberately excluded.

## Non-goals

- Generic storage-provider abstraction.
- Compatibility `/files/*` APIs.
- File-level category semantics.
- Video as a Core dependency.
- Country/region detection in application logic.
- Full payload downloads during ordinary indexing.
