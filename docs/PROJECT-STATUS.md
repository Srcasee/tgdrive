# Project Status

Updated 2026-08-31 after the Resource migration cleanup, delivery boundary cleanup, account lifecycle work, and CI verification. The project is ready to enter the first real-device testing phase.

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
- Enabled account state is reconciled with runtime clients and scanner tasks: implemented.

### Ingestion and Resource identity

- Telegram message recognition and metadata normalization: implemented.
- `TelegramFileObservation` boundary: implemented.
- Provisional metadata identity: implemented.
- Logical Resource persistence: implemented.
- Physical Telegram locations remain separate from logical Resources: implemented.
- SHA-256 streaming verification utility: implemented.
- Complete non-range delivery performs content verification and canonical Resource promotion: implemented.

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
- Resource streaming: implemented through the same direct Telegram source path as download.
- Multiple Telegram backing locations: implemented.
- Safe pre-transfer failover: implemented.
- Complete non-range delivery verifies content after the response body is consumed.
- Core delivery has no Video/chunk-cache dependency.

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

Accounts are redundant access paths, not storage providers. Enabled state is reconciled with runtime Telegram clients and scanner tasks. Administrators can enable/disable accounts and explicitly reconnect clients. Automated health scoring remains deferred because it should be driven by real-device measurements.

### Proxy

The external Proxy plugin boundary remains optional. Proxy configuration changes can be applied by explicitly reconnecting Telegram clients. Video is not part of the Core runtime mount.

### Legacy cleanup

The active code path no longer exposes the obsolete File-centric HTTP/admin surface. The physical `files` database table remains because it represents Telegram-backed locations; it is accessed through `TelegramFileRepository` and is not a public Resource API.

Removed from the active surface:

- `/files/*` browser/API routes
- admin `PUT /api/admin/files/{file_id}/category`
- `CategoryRepository.assign_file()`
- obsolete `FileRepository` naming/path in favor of `TelegramFileRepository`
- unused `app/cache` package
- Core chunk-cache/Video delivery implementation
- obsolete single-session `TG_SESSION` configuration

## CI gate

The latest PostgreSQL integration workflow passed on both Python 3.11 and Python 3.12. The full test suite and proxy plugin image build passed in workflow run #312 on commit `d6a49b2574cfe397a6cf593c81219ca5a905b53d`.

This is the code-level gate for entering real-device testing. CI success does not substitute for Telegram/network validation on real hardware.

## Deferred work after real-device measurements

### P2 — Resource-level source policy

Failover currently uses basic source ordering. Add explicit health signals, transient retry policy, and richer ranking only after real-device measurements justify them. Issue #19.

### P2 — Scanner/Ingestion boundary refinement

The core boundary is sufficient for real-device testing. Further reduction of orchestration coupling is deferred unless deployment behavior demonstrates a concrete need. Issue #15.

### P2 — source scheduling

`telegram_sources.scan_interval` is persisted but the scanner currently uses a global account scan interval. Align scheduling only if real deployment requirements justify it.

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
9. Complete-download SHA-256 promotion
10. Proxy connectivity/reconnect when required
```

Video is intentionally excluded from this sequence.

## Real-device readiness

**READY.** There are no remaining P1 architecture items that block the first real-device validation. Remaining open architecture work is deliberately P2 and should be informed by real-device observations rather than speculative optimization.