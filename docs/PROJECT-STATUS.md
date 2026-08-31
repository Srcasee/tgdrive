# Project Status

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

No generic storage-provider abstraction is required or planned.

## Current implementation status

### Telegram discovery

- Account-named Telethon sessions: implemented.
- Explicit source configuration by account + Telegram chat ID: implemented.
- Incremental scanning: implemented.
- Full-sync failure-safe reconciliation: implemented.
- Scanner failure state: implemented.
- Traversal is metadata-only: implemented.

### Ingestion and Resource identity

- Telegram message recognition and metadata normalization: implemented.
- `TelegramFileObservation` boundary: implemented.
- Provisional metadata identity: implemented.
- Logical Resource persistence: implemented.
- Physical Telegram locations remain separate from logical Resources: implemented.
- SHA-256 streaming verification utility: implemented.
- End-to-end canonical Resource promotion after complete delivery: **not yet closed**; issue #24.

### Catalog and classification

- Resource-centric listing: implemented.
- Resource-centric filename search: implemented.
- Resource categories via `resource_categories`: implemented.
- Category filtering: implemented.
- Resource detail/source count: implemented.
- Admin Resource-to-category assignment: implemented.
- Live `files.category_id` column: removed.
- Legacy file-level category endpoint: removed.

### Delivery

- Resource-centric download: implemented.
- HTTP Range: implemented.
- Resource streaming: implemented.
- Multiple Telegram backing locations: implemented.
- Safe pre-transfer failover: implemented.
- Delivery no longer loads the Video plugin: implemented.

### Web UI

The previous File-oriented browser was replaced with a dependency-free Resource-first UI.

Core UI supports:

- login/session bootstrap
- catalog browsing
- filename search
- category filtering for administrators
- Resource download
- share-link creation
- Resource category assignment for administrators

Video playback is deliberately absent from the current Core UI.

### Telegram accounts

Accounts are redundant access paths, not storage providers. Enabled state is respected when clients are created. Complete administrator lifecycle and health behavior remains issue #18.

### Proxy

The external Proxy plugin boundary remains available. The normal Compose service mounts only the Proxy plugin; Video is not part of the Core runtime mount.

### Legacy cleanup

The active code path no longer exposes the obsolete File-centric HTTP/admin surface. The physical `files` database table remains because it represents Telegram-backed locations; it is accessed through `TelegramFileRepository` and is not a public Resource API.

Removed from the active surface:

- `/files/*` browser/API routes
- admin `PUT /api/admin/files/{file_id}/category`
- `CategoryRepository.assign_file()`
- obsolete `FileRepository` naming/path in favor of `TelegramFileRepository`
- unused `app/cache` package
- Video cache dependency from Core delivery

## Remaining gaps

### P1 — canonical content identity promotion

Complete the explicit full-byte verification → SHA-256 Resource promotion/merge lifecycle. Issue #24.

### P1 — account lifecycle and health

Complete enable/disable/retire/remove administration and explicit runtime reconnect/re-enable behavior. Issue #18.

### P1 — ingestion separation

Scanner still owns some scan orchestration. The target boundary remains Telegram traversal → observation, with Ingestion owning recognition/persistence semantics.

### P1 — proxy reconnect

Changing proxy configuration requires explicit Telegram client recreation/reconnect. Issue #20.

### P1/P2 — delivery source policy

Failover currently uses basic source ordering. Health/latency scoring should be driven by real-device measurements before optimization. Issue #19.

### P2 — source scheduling

`telegram_sources.scan_interval` is persisted but the scanner currently uses a global interval. Align scheduling only if real deployment requirements justify it.

### P2 — transport optimization

Do not tune concurrency or caching before real-device delivery behavior is measured. Issue #21.

### P2 — package namespace

The top-level `telegram` Python package can collide with third-party packages. This is a packaging concern only. Issue #22.

## Real-device test priority

```text
1. Core + PostgreSQL health
2. Telegram login/session reuse
3. Explicit source configuration
4. Metadata-only scan
5. Resource catalog/search/classification
6. Single-source download
7. Multi-account failover
8. HTTP Range behavior
9. Proxy connectivity when required
```

Video is intentionally excluded from this sequence.
