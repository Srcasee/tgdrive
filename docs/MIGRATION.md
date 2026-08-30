# TGDrive Migration / Architecture Convergence Record

Updated after the architecture/code convergence review on 2026-08-30.

## Product definition

tgdrive is a **Telegram-only** file catalog and delivery system.

```text
Telegram storage
      |
      v
System recognition / ingestion
      |
      v
Resource catalog + classification
      |
      +----> Web search / browse
      |
      +----> Download / streaming
```

Telegram is the only content backend. No generic storage-provider abstraction is planned.

## Core architecture

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

## Architectural principle

> **Telegram Message is the physical source record; Resource is the system-recognized business entity; Category organizes Resources; Delivery consumes a Resource; Telegram Account is an access/redundancy path; Proxy is a Telegram connectivity policy; User/Admin Auth controls who may use or manage the system.**

Scanning is metadata-only. A first scan of a large Telegram file must never download the complete payload to the application server. Content verification happens only when a real transfer/verification operation is requested.

## Current implementation mapping

### Telegram access and account path

Implemented in `app/telegram/`, `app/repositories/accounts.py`, and lifecycle code. Session discovery is automatic and only enabled database accounts are loaded as clients. Admin account lifecycle operations remain incomplete.

### Ingestion / recognition

`app/telegram/scanner.py` traverses configured Telegram sources and produces observations through `TelegramMessageRecognizer`. `app/ingestion/service.py` owns recognition/persistence coordination, while `app/repositories/resources.py` owns Resource identity and verification persistence.

This is substantially migrated from the old scanner-direct-to-file model, but scanner orchestration still contains some source/scan-state responsibilities. Further separation is planned without changing the target domain boundaries.

### Resource

Implemented. `resources` is a logical entity separate from the physical `files` Telegram location. Provisional identity is deterministic from normalized metadata; verified identity is SHA-256 based. A verified physical file keeps its Resource association across later scanner rescans.

### Redundancy

Implemented at the data and Delivery layers. Multiple physical `files` rows may point to the same Resource. `files.account_id` uses `ON DELETE SET NULL`, so removing an account does not cascade-delete the physical metadata or logical Resource.

### Catalog / classification / search

Implemented in `app/catalog/` and `app/admin/api.py`. Categories are attached through `resource_categories`, not the old physical `files.category_id`. Catalog listing/search returns logical Resources and can filter by Resource category and usable-source availability.

Search is currently filename-oriented; richer Resource search fields are still optional future work.

### Delivery

Implemented in `app/delivery/`. User endpoints operate on Resource IDs, apply authentication and availability checks, and support HTTP Range semantics. `TelegramSourceSelector` evaluates multiple Telegram-backed locations.

Failover is safe before a response has emitted bytes. Once bytes have been emitted, a failed source is not restarted from the original offset because doing so would duplicate bytes in the HTTP response. A future resumable transport can improve this without changing the Resource model.

### Content verification

Implemented as a separate Resource promotion operation. Verification of one physical Telegram location does not overwrite unrelated Resource identities. If the verified SHA-256 already belongs to another Resource, the physical location is moved to that verified Resource and an empty provisional Resource is removed.

### Proxy

Implemented as an external plugin under `plugins/proxy/`, discovered through the generic plugin runtime. Direct connectivity is the default. Proxy is enabled by deployment configuration; Core performs no country/region detection. Existing Telethon clients retain the proxy captured at construction, so configuration changes require explicit client recreation/reconnect.

### Optional Video capability

Video chunk caching is outside Core under `plugins/video/` and is exposed as an optional `delivery.chunk-cache` capability. Core remains functional without it.

### Web Auth

Implemented under `app/auth/` as a cross-cutting access-control layer. It does not own Telegram credentials, Resource identity, Categories or Delivery source selection.

## Current repository tree

```text
app/
├── admin/                 # administrator HTTP operations
├── auth/                  # Web authentication/authorization
├── catalog/               # Resource catalog, categories, search API/service
├── common/                # shared HTTP response helpers
├── core/                  # application composition and lifecycle
├── delivery/              # Resource download, Range, streaming, source selection
├── ingestion/             # recognition and Resource identity orchestration
├── repositories/          # PostgreSQL persistence implementations
├── telegram/              # Telegram client, login, scanner, downloader, source API
├── web/                   # browser UI
├── config.py              # deployment configuration
├── database.py            # schema migrations
└── database_pool.py       # PostgreSQL pool

plugins/
├── proxy/                 # optional Telegram connectivity plugin
└── video/                 # optional delivery chunk-cache plugin
```

There is no Core `app/files` module in the current architecture.

## Remaining gaps

1. Complete Telegram account enable/disable/retire/remove administration and expose health state safely.
2. Finish moving scanner orchestration concerns out of `app/telegram/scanner.py` so Ingestion owns recognition semantics while Telegram owns traversal.
3. Expand Resource-oriented search only when product requirements justify additional metadata.
4. Add explicit Telegram client reconnect/rebuild semantics for proxy configuration changes.
5. Measure Delivery throughput across multiple valid Telegram paths before introducing aggressive concurrency or cache behavior.
6. Resolve the top-level `telegram` Python package namespace collision as a packaging concern.

## Deployment direction

The normal deployment should remain deliberately small:

```text
.env
  |
  v
docker compose up -d --build
  |
  +--> PostgreSQL
  +--> tgdrive Core

Optional:
  docker compose --profile proxy up -d --build
```

No manual PostgreSQL SQL or manual account-row creation is required for the normal path. Telegram login is the only interactive bootstrap step because Telegram may require an OTP/2FA challenge.

## Target architecture is unchanged

This migration record describes implementation status only. It does **not** redefine the target architecture or introduce additional storage backends.
