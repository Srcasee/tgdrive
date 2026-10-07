# Stage 1 — Architecture Convergence Record

Updated 2026-08-31.

This document is a historical phase record. The current source of truth is `README.md`, `docs/ARCHITECTURE.md`, and `docs/PROJECT-STATUS.md`.

## Converged Core

The active Core path is now:

```text
Telegram metadata
   ↓
Recognition / Ingestion
   ↓
Logical Resource
   ↓
Catalog / classification / search
   ↓
Resource download / Range delivery
   ↓
Telegram backing locations
```

The public API and browser UI are Resource-first. The physical `files` table remains only as the persistence representation of Telegram-backed locations.

## Cleanup completed after Stage 1

- Removed legacy `/files/*` browser/API paths.
- Removed the old file-level category admin endpoint.
- Removed `files.category_id` from the live schema.
- Renamed the physical Telegram file persistence adapter to `TelegramFileRepository`.
- Replaced the old File-oriented Web UI with a Resource-first UI.
- Updated account login to use account-named sessions.
- Removed the Video cache dependency from Core delivery.
- Normal Compose runtime mounts only the optional Proxy plugin.

## Video decision

Video playback and chunk caching are not part of the current real-device testing scope.

The optional Video plugin remains outside Core and is not mounted by the normal service. Core cataloging, scanning, Resource identity and ordinary download/Range delivery do not require Video.

If Video work resumes later, it must be integrated around the delivery boundary without adding Video-specific state or behavior to Core.

## Real-device focus

The active test sequence is intentionally:

```text
Core + PostgreSQL
      ↓
Telegram session reuse
      ↓
Explicit source configuration
      ↓
Metadata-only scan
      ↓
Resource catalog/search/classification
      ↓
Single-source delivery
      ↓
Multi-account failover
      ↓
HTTP Range
      ↓
Proxy only when required
```

Transport optimization remains deferred until real-device measurements justify it.
