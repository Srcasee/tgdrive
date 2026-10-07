# Features and Target Capabilities

## Current Core

| Capability | Status | Notes |
|---|---|---|
| Telegram private-source scanning | Implemented | Telethon sessions + explicit source scanner |
| PostgreSQL metadata index | Implemented | Physical Telegram locations, Resource identity, availability and scan state |
| Metadata-only recognition/Ingestion | Implemented | Full Telegram payloads are not downloaded during ordinary indexing |
| Logical Resource model | Implemented | Physical Telegram locations are separate from logical Resources |
| Resource catalog | Implemented | Resource-centric list/detail/search |
| Filename search | Implemented | Basic filename `ILIKE` search with optional category filter |
| Resource classification | Implemented | `resource_categories` + admin Resource assignment |
| Download | Implemented | Streaming from available Telegram backing locations |
| HTTP Range | Implemented | Download and stream endpoints |
| Multi-account Telegram paths | Implemented | Accounts are access/redundancy paths |
| Pre-transfer source failover | Implemented | Does not restart after response bytes have been emitted |
| Proxy plugin boundary | Implemented | Optional deployment connectivity plugin |
| Resource-first Web UI | Implemented | Dependency-free browser client for real-device testing |
| Web authentication | Implemented | Cross-cutting user/admin access control |
| Content verification utility | Implemented | SHA-256 streaming verification; canonical promotion remains issue #24 |

## Current real-device testing scope

The core test path is:

```text
Telegram account/session
       ↓
Telegram source configuration
       ↓
Metadata-only scan
       ↓
Logical Resource catalog
       ↓
Search / classification
       ↓
Download / HTTP Range
       ↓
Multiple Telegram source failover
```

Video playback and chunk caching are **not** part of this test scope.

## Administration

Current Resource-level administration includes:

```text
Admin login
  -> category CRUD
  -> assign categories to Resources
```

Telegram account lifecycle and health controls remain tracked separately in issue #18.

## Optional connectivity

```text
Core Telegram client
       ↓
Direct connection
       or
Proxy plugin
```

Proxy is deployment-controlled. Core does not infer geographic requirements or implement concrete proxy protocols.

## Optional Video

The Video plugin is intentionally outside the Core delivery path. It is not mounted by the normal Compose service and must not be required for cataloging, scanning, Resource identity, download or Range delivery.

If Video work resumes later, it should integrate as an adapter around the delivery boundary rather than adding Video-specific state or behavior to Core.

## Explicit non-goals

- Generic storage-provider abstraction.
- Compatibility `/files/*` APIs.
- File-level category semantics.
- Video as a Core dependency.
- Country/region detection in application code.
- Downloading full Telegram payloads during ordinary indexing.
