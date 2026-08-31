# tgdrive Architecture

## Product boundary

tgdrive is a **Telegram-only** file catalog and delivery system.

Telegram is the only content backend. There is no generic storage-provider abstraction for S3, WebDAV, Google Drive, or other backends.

The product flow is:

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
Physical Telegram backing locations
```

PostgreSQL stores metadata, classification and source state. Telegram remains the source of file bytes. Ordinary scanning is metadata-only.

## Domain priorities

1. **Ingestion / recognition** — discover Telegram media, normalize metadata, identify Resources and maintain physical-location state.
2. **Logical Resource** — represent one system-level content entity independently of its Telegram message locations.
3. **Catalog / classification** — organize Resources and expose Resource-oriented search/browse.
4. **Delivery** — retrieve Resource bytes through available Telegram locations with HTTP Range support and safe pre-transfer failover.
5. **Telegram accounts** — provide redundant access paths, with explicit enable/disable and reconnect lifecycle.
6. **Connectivity / proxy** — optional deployment infrastructure.
7. **Web authentication** — cross-cutting access control; not part of the content domain.

Video is an optional future capability and is intentionally outside the Core delivery path and current real-device testing scope.

## Domain relationship

```text
                         Web User
                            │
                     Search / Browse
                            │
                            ▼
                     Catalog / Admin
                            │
                            ▼
                      Logical Resource
                            ▲
                            │
                     Recognition/Ingestion
                            ▲
                            │
                     Telegram metadata
                            │
             ┌──────────────┼──────────────┐
             │              │              │
         Account A      Account B      Account C
             │              │              │
             └──────────────┼──────────────┘
                            │
                       Telegram API
                            │
                      Direct / Proxy

Delivery:

Resource
   ↓
available Telegram locations
   ↓
source selection / failover
   ↓
Telegram bytes
   ↓
HTTP response
```

## Architectural principle

> **Telegram Message is the physical source record; Resource is the system-recognized business entity; Category organizes Resources; Delivery consumes a Resource; Telegram Account is an access/redundancy path; Proxy is a connectivity policy.**

The physical `files` table remains a persistence representation of Telegram-backed locations. It is not the public domain/API model.

## Module layout

```text
app/
├── core/                         # application composition + lifecycle
├── auth/                         # Web access control
├── telegram/                     # Telegram integration
│   ├── client.py
│   ├── login.py
│   ├── scanner.py
│   ├── downloader.py
│   └── api.py
├── ingestion/                    # recognition / normalization / identity
│   ├── recognizer.py
│   ├── identity.py
│   ├── models.py
│   ├── service.py
│   └── verification.py
├── catalog/                      # Resource catalog/search
│   ├── api.py
│   ├── repository.py
│   └── service.py
├── delivery/                     # Resource retrieval
│   ├── api.py
│   ├── source_selector.py
│   └── range.py
├── repositories/                 # PostgreSQL persistence adapters
│   ├── resources.py
│   ├── telegram_files.py
│   ├── accounts.py
│   ├── sources.py
│   ├── categories.py
│   └── shares.py
├── admin/                        # administrator HTTP adapter
├── web/                          # browser UI
├── plugins/                      # optional plugin runtime contracts
├── config.py
├── database.py
└── database_pool.py

plugins/
└── proxy/                        # optional Telegram connectivity implementation
```

The optional Video plugin is not part of the Core runtime or normal Compose service.

## Implementation mapping

| Responsibility | Current implementation | Status |
|---|---|---|
| Telegram accounts/sessions | `app/telegram/client.py`, `app/telegram/login.py`, `app/repositories/accounts.py` | Implemented; enabled accounts are reconciled with runtime clients and scanner tasks. |
| Telegram source configuration | `app/telegram/api.py`, `app/repositories/sources.py` | Implemented; physical source identity is account + Telegram chat. |
| Scanner/discovery | `app/telegram/scanner.py` | Implemented; Telegram traversal produces observations and delegates recognition/persistence to Ingestion. |
| Recognition/identity | `app/ingestion/*`, `app/repositories/resources.py` | Implemented; provisional metadata identity and verified SHA-256 identity are distinct. |
| Logical Resource | `resources` + `app/repositories/resources.py` | Implemented; independent of physical Telegram locations. |
| Physical Telegram location persistence | `files` + `app/repositories/telegram_files.py` | Implemented; physical storage details stay behind the Resource boundary. |
| Catalog | `app/catalog/*` | Implemented; listing/search operate on logical Resources. |
| Classification | `resource_categories` + `app/admin/api.py` + `CatalogRepository.set_categories()` | Implemented at Resource level; `files.category_id` is removed. |
| Delivery | `app/delivery/*` | Implemented; Resource IDs are the public delivery key. |
| Source selection/failover | `app/delivery/source_selector.py` | Implemented for failures before response bytes are emitted. |
| Content verification | `app/ingestion/verification.py`, `ResourceRepository.verify_file()` | Implemented for complete non-range delivery; successful full delivery promotes the physical location to SHA-256 identity. |
| Proxy | `plugins/proxy/`, `app/plugins/runtime.py` | Optional and deployment-controlled; explicit `/api/telegram/reconnect` rebuilds clients after proxy changes. |
| Web UI | `app/web/index.html` | Resource-first, responsive, no dependency on Video. |
| Web Auth | `app/auth/*` | Cross-cutting and isolated from content semantics. |

## Resource and physical-location model

```text
accounts
    │
    ├── telegram_sources
    │
    └── files ───────────────┐
                             │ resource_id
                             ▼
                          resources
                             │
                             ▼
                    resource_categories
                             │
                             ▼
                         categories
```

Physical Telegram identity is `(account_id, telegram_chat_id, message_id)`. A logical Resource may have multiple physical locations.

Resource identity has two stages:

```text
metadata-only scan
      ↓
index:<normalized metadata>
      ↓
complete content verification
      ↓
sha256:<digest>
```

The scanner must never download a complete file merely to build an index. A partial HTTP Range cannot establish a full-content identity.

## Delivery contract

The public delivery contract is Resource-first:

```text
GET/HEAD /resources/{resource_id}/download
GET/HEAD /resources/{resource_id}/stream
POST     /resources/{resource_id}/share
```

Delivery resolves a Resource to available Telegram-backed locations and chooses a usable source. If a source fails before bytes are emitted, another location can be tried. Once bytes have been emitted, transparent restart from the original offset is not attempted because it would duplicate bytes in the HTTP response.

Both download and stream use the same direct Telegram source path. Core delivery has no chunk-cache or Video dependency. Complete, non-range transfers hash the emitted bytes and promote the physical source to its canonical SHA-256 Resource identity after the response body is consumed.

## Web UI contract

The browser UI is intentionally a small, dependency-free Resource client:

```text
/auth/login + /auth/me
        ↓
/catalog + /catalog/search
        ↓
/resources/{id}/download
/resources/{id}/share
        ↓
/admin Resource classification (admin only)
```

There are no legacy `/files/*` browser/API paths.

## Telegram account lifecycle

The runtime reconciles database account state with in-process Telegram clients:

```text
accounts.enabled
      ↓
client creation / removal
      ↓
scanner task creation / cancellation
```

Administrators can explicitly enable or disable an account and request a full client reconnect. A reconnect rebuilds clients so current proxy/account configuration is applied.

## Proxy boundary

```text
Telegram client
      ↓
connectivity policy
   ┌──┴──┐
Direct Proxy plugin
```

Core does not perform country/region detection or implement concrete proxy protocols. Proxy is selected by deployment configuration. Because Telegram clients capture proxy settings at construction, proxy changes take effect through explicit client recreation/reconnect.

## Deferred work

### P2 — source scheduling/selection depth

Per-source scheduling and richer health/latency scoring can be improved after real-device measurements.

### P2 — transport optimization

Do not optimize concurrency or add caching before Resource source selection and real-device delivery behavior are measured.

## Intentionally excluded from Core

- Generic storage-provider abstraction.
- Video playback/cache implementation.
- Country/region detection.
- Account-as-storage-provider semantics.
- Compatibility `/files/*` APIs.
- Downloading full Telegram payloads during ordinary indexing.
