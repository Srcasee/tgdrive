# tgdrive Architecture

## Product boundary

tgdrive is a Telegram-only file catalog and delivery system.

Telegram is the only content backend. The project does **not** use a generic storage-provider abstraction for S3, WebDAV, Google Drive, or other backends.

The product flow is:

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

PostgreSQL stores metadata, classification and source state. Telegram remains the source of file bytes. Scanning is metadata-only; the application does not download complete files merely to index them.

## Domain priorities

1. **Ingestion / system recognition** — discover Telegram media, normalize metadata, identify logical Resources and maintain physical-location availability.
2. **Catalog / classification** — organize Resources into categories and expose Resource-oriented search/browse.
3. **Delivery** — retrieve bytes from Telegram only when requested, with source selection/failover and HTTP Range streaming.
4. **Telegram accounts** — provide redundancy and optional alternative delivery paths. Multiple accounts are not storage backends.
5. **Connectivity / proxy** — optional deployment infrastructure used only when the server/network requires it.
6. **Web authentication / authorization** — cross-cutting access control for users and administrators; not a core domain.

## Domain relationship

```text
                         +------------------+
                         |    Web User      |
                         +--------+---------+
                                  |
                           Search / Download
                                  |
                                  v
                       +----------------------+
                       |       Catalog        |
                       | Resource / Category  |
                       | Search / metadata    |
                       +----------+-----------+
                                  ^
                                  |
                           System recognition
                                  |
                       +----------+-----------+
                       |      Ingestion       |
                       | Scanner / Recognizer |
                       | Normalize / Identify |
                       +----------+-----------+
                                  |
                           Telegram messages
                                  |
                +-----------------+-----------------+
                |                 |                 |
                v                 v                 v
            TG Account A      TG Account B      TG Account C
                |                 |                 |
                +-----------------+-----------------+
                                  |
                           Telegram API
                                  |
                           Connectivity
                                  |
                         +--------+--------+
                         |                 |
                      Direct         Proxy plugin
```

## Architectural principle

> **Telegram Message is the physical source record; Resource is the system-recognized business entity; Category organizes Resources; Delivery consumes a Resource; Telegram Account is an access/redundancy path; Proxy is a Telegram connectivity policy; User/Admin Auth controls who may use or manage the system.**

## Target module layout

The following remains the target boundary. It is not a claim that every target filename exists yet.

```text
app/
|
+-- core/                         # application composition + lifecycle
|
+-- auth/                         # cross-cutting Web access control
|
+-- telegram/                     # Telegram-only backend integration
|   +-- client.py
|   +-- login.py
|   +-- scanner.py
|   +-- downloader.py
|   +-- api.py
|
+-- ingestion/                    # recognition / normalization / identity
|   +-- recognizer.py
|   +-- service.py
|
+-- catalog/                      # Resource-oriented catalog API/service
|   +-- api.py
|   +-- repository.py
|   +-- service.py
|
+-- delivery/                     # user-facing retrieval from Resource sources
|   +-- api.py
|   +-- source_selector.py
|   +-- streaming.py
|   +-- range.py
|
+-- repositories/                 # current PostgreSQL persistence implementation
|   +-- resources.py
|   +-- files.py
|   +-- accounts.py
|   +-- sources.py
|   +-- categories.py
|
+-- admin/                        # administrator HTTP adapter
+-- web/                          # browser UI
+-- plugins/                      # plugin runtime contracts inside Core

plugins/
+-- proxy/                        # optional Telegram connectivity implementation
+-- video/                        # optional delivery chunk-cache capability
```

## Current implementation mapping

| Responsibility | Current implementation | Status |
|---|---|---|
| Telegram account/session access | `app/telegram/client.py`, `app/telegram/login.py`, `app/repositories/accounts.py` | **Implemented**; enabled accounts are filtered when clients are created. Full admin lifecycle API is still incomplete. |
| Telegram source configuration | `app/telegram/api.py`, `app/repositories/sources.py` | **Implemented**; physical source identity is account + Telegram chat. |
| Scanner/discovery | `app/telegram/scanner.py` | **Implemented**; traverses configured chats and performs metadata-only discovery. It delegates recognition/persistence to Ingestion but still owns some scan orchestration. |
| Recognition / identity | `app/ingestion/recognizer.py`, `app/ingestion/service.py`, `app/repositories/resources.py` | **Implemented**; deterministic provisional identity and SHA-256 content identity are separate. Verified physical locations retain their Resource identity across rescans. |
| Logical Resource | `resources` table + `app/repositories/resources.py` | **Implemented**; Resource is separate from physical Telegram file/message location. |
| Resource redundancy | `files.resource_id` + `ResourceRepository.verify_file()` + source listing | **Implemented at data/delivery level**; one Resource can have multiple Telegram-backed file locations. Account deletion uses `ON DELETE SET NULL` for file metadata. |
| Catalog | `app/catalog/api.py`, `app/catalog/repository.py`, `app/catalog/service.py` | **Implemented**; lists and searches logical Resources and reports usable source counts. |
| Classification | `resource_categories` + `app/admin/api.py` + `CatalogRepository.set_categories()` | **Implemented** at Resource level. The old physical `files.category_id` column has been removed. |
| Search | `CatalogRepository.search_resources()` | **Implemented**, currently filename-oriented with optional Resource category filtering. |
| Delivery | `app/delivery/api.py`, `app/delivery/streaming.py`, `app/delivery/range.py` | **Implemented**; Resource-centric download/stream endpoints and Range semantics. |
| Source selection/failover | `app/delivery/source_selector.py` | **Implemented** for pre-transfer source failure. A source that fails after bytes have been emitted is not transparently retried, preventing duplicate/corrupt HTTP bodies. |
| Content verification | `app/repositories/resources.py` | **Implemented** as an explicit verification/promotion operation. Scanning itself does not download payloads. |
| Proxy boundary | `app/plugins/runtime.py`, `plugins/proxy/` | **Implemented**; concrete proxy code is external to the Core Telegram domain. |
| Proxy deployment policy | environment + optional Compose `proxy` profile | **Implemented** as deployment configuration. Core does not infer country/region requirements. Reconnect semantics for changing an already-created client remain explicit/lifecycle-bound. |
| Optional video cache | `plugins/video/` + plugin capability `delivery.chunk-cache` | **Optional plugin**; not required by Core or deployment. |
| Web Auth | `app/auth/*` | **Implemented** and intentionally cross-cutting. |
| Admin | `app/admin/api.py` | **Partial**; Resource category management exists; Telegram account lifecycle management is not complete. |

## Current data model

```text
accounts
    |
    +-- telegram_sources
    |
    +-- files --------------------+
           |                      |
           +-- resource_id ------> resources
                                  |
                                  +-- resource_categories --> categories
```

Physical file identity remains `(account_id, telegram_chat_id, message_id)`. Logical Resource identity is represented separately by `resources.identity_key`, initially using normalized metadata and, after verification, SHA-256 content identity.

This gives the required distinction:

```text
Telegram physical location
        |
        +-- account/chat/message
        |
        v
Physical file row
        |
        +-- resource_id
        v
Logical Resource
```

## Telegram accounts

Multiple accounts primarily provide:

1. **Availability / redundancy** — a Resource may have multiple Telegram-backed locations.
2. **Delivery optimization** — Delivery may choose among usable locations later using health/throughput signals.

Account enablement is enforced when clients are created. Disabled accounts therefore are not normal scanner/delivery access paths, while their physical metadata can remain attached to a Resource.

## Proxy plugin boundary

```text
Telegram client
      |
      v
 Connectivity request
      |
   +--+--+
   |     |
Direct  Proxy plugin
```

Core contains no country/region detection and no concrete proxy protocol implementation. The administrator/deployment chooses direct or proxy according to server/network requirements. The current external plugin supports SOCKS5/HTTP local endpoints and can run a sing-box upstream.

Changing proxy configuration requires Telegram client recreation/reconnect; refreshing the plugin registry alone does not mutate an already-created Telethon client.

## Web authentication boundary

```text
username/password
      |
      v
PBKDF2 password hash
      |
      v
signed expiring session token
      |
      v
HttpOnly cookie
      |
      v
Principal(subject, role)
      |
      +---- user -> Catalog / Delivery
      |
      +---- admin -> Catalog / Telegram management
```

Auth does not own Telegram sessions, Resources, Categories or source selection.

## Remaining implementation gaps

### P1 — complete Telegram account lifecycle

Client loading now respects `accounts.enabled`, but administrator operations for enable/disable/retire/remove and account health inspection are not yet a complete API surface. Account lifecycle must continue to preserve Resource metadata and make disabled access paths unavailable.

### P1 — finish ingestion separation

`IngestionService` and `TelegramMessageRecognizer` now provide the recognition boundary, but `app/telegram/scanner.py` still coordinates scan state, source selection and the Ingestion call. Further separation should make Telegram traversal produce observations while Ingestion owns recognition and persistence semantics.

### P1 — broaden Resource catalog semantics

Catalog is Resource-oriented and category assignment is Resource-level, but search is still primarily filename + category. Additional metadata fields should be added only when required by product behavior.

### P1 — proxy reconnect operation

Proxy is correctly isolated and deployment-controlled. An explicit lifecycle operation is still needed to safely rebuild existing Telegram clients after proxy configuration changes.

### P2 — transport optimization

Delivery failover exists, but throughput optimization should be measured across valid Telegram paths before introducing more aggressive concurrency or caching.

### P2 — top-level `telegram` package namespace

The application package name remains potentially collision-prone with third-party Python packages. This is a packaging concern, not a reason to introduce a generic Telegram/storage abstraction.

## Intentionally rejected

- Generic storage-provider abstraction.
- Country/region detection embedded in application code.
- Account-scoped proxy policy as a default requirement.
- Treating Telegram accounts as storage backends.
- Treating Web users and Telegram accounts as one authentication model.
- Making Video a Core capability.

## Work order

1. Introduce/complete logical Resource + Telegram backing-location model.
2. Complete ingestion/recognition boundaries and deterministic identity.
3. Move classification/search behavior to Resource/Catalog semantics.
4. Complete Telegram account lifecycle and health state.
5. Complete Delivery source selection/failover across Telegram locations.
6. Finish deployment-level proxy configuration/reconnect semantics.
7. Optimize transport only after Resource/Delivery source selection is stable.
8. Keep Web Auth isolated and stable unless a concrete security defect is found.
