# tgdrive Architecture

## Product boundary

tgdrive is a Telegram-only file catalog and delivery system.

Telegram is the only content backend. The project does **not** need a generic storage-provider abstraction for S3, WebDAV, Google Drive, or other backends. Such abstraction would add complexity without serving the current product.

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

PostgreSQL stores the system's metadata, classification and source state. Telegram remains the source of file bytes.

## Domain priorities

1. **Ingestion / system recognition** — discover Telegram media, normalize metadata, identify resources and maintain their availability.
2. **Catalog / classification** — organize recognized resources into categories and make them searchable.
3. **Delivery** — retrieve bytes from Telegram efficiently for downloads and streaming.
4. **Telegram accounts** — provide source redundancy and optional throughput optimization. Multiple accounts are not multiple storage backends; they are multiple access paths to Telegram content.
5. **Connectivity / proxy** — optional deployment infrastructure used only when the deployment's network requires it.
6. **Web authentication / authorization** — cross-cutting access control for users and administrators. It is not a core domain.

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
                       |                      |
                       | Resource             |
                       | Category             |
                       | Search / metadata    |
                       +----------+-----------+
                                  ^
                                  |
                           System recognition
                                  |
                       +----------+-----------+
                       |      Ingestion       |
                       |                      |
                       | Scanner              |
                       | Parser / normalizer  |
                       | Dedup / identification|
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

Authentication/authorization is a cross-cutting boundary around the Web/API side:

```text
                         +-------------+
                         |    Auth     |
                         +------+------+ 
                                |
                    +-----------+-----------+
                    |                       |
                    v                       v
                  User                    Admin
                    |                       |
                    v                       v
             Search / Download       Catalog / TG management
```

## Architectural principle

The central rule is:

> **Telegram Message is the physical source record; Resource is the system-recognized business entity; Category organizes Resources; Delivery consumes a Resource; Telegram Account is an access/redundancy path; Proxy is a Telegram connectivity policy; User/Admin Auth controls who may use or manage the system.**

This distinction prevents Telegram message records, business resources, accounts and web users from becoming one overloaded concept.

## Target module layout

```text
app/
|
+-- core/
|   +-- app.py
|   +-- lifecycle.py
|   +-- config.py
|   +-- exceptions.py
|
+-- auth/                         # cross-cutting access control
|   +-- api.py
|   +-- security.py
|   +-- dependencies.py
|   +-- models.py
|   +-- policy.py
|   +-- repository.py
|
+-- telegram/                     # only content backend
|   +-- api.py
|   +-- client.py
|   +-- scanner.py
|   +-- downloader.py
|   +-- login.py
|   +-- check_sessions.py
|
+-- ingestion/                    # target: first core domain
|   +-- discovery.py
|   +-- parser.py
|   +-- normalizer.py
|   +-- deduplicator.py
|   +-- service.py
|
+-- catalog/                      # target: first core domain
|   +-- resources.py
|   +-- categories.py
|   +-- search.py
|   +-- service.py
|   +-- repository.py
|
+-- delivery/                     # target: core user capability
|   +-- download.py
|   +-- source_selector.py
|   +-- streaming.py
|   +-- range.py
|
+-- connectivity/                 # target: Telegram network boundary
|   +-- interface.py
|   +-- direct.py
|   +-- registry.py
|
+-- plugins/                      # optional infrastructure capabilities
|   +-- interface.py
|   +-- runtime.py
|
+-- repositories/                 # current persistence layer; to be split by domain
|
+-- admin/                        # HTTP adapter for admin operations
|
+-- web/                          # browser UI
|
plugins/
  +-- proxy/                     # optional external proxy implementation
```

The layout above is the **target boundary**, not a claim that all target modules already exist. Current implementation mapping and gaps are documented below.

## Current implementation mapping

| Target responsibility | Current implementation | Status / finding |
|---|---|---|
| Telegram account/session access | `app/telegram/client.py`, `app/telegram/login.py`, `repositories/accounts.py` | Implemented, but account lifecycle is coupled to session-file discovery |
| Telegram source selection | `app/telegram/api.py`, `repositories/sources.py` | Implemented; source is `(account_id, telegram_chat_id)` |
| System recognition / scanning | `app/telegram/scanner.py` | Implemented as Telegram-specific scanner; normalization/dedup/resource recognition are not separate domain services |
| Resource identity | `files` table + `FileRepository` | **Missing as a business concept**; current identity is physical `(account_id, telegram_chat_id, message_id)` |
| Resource redundancy | `files.account_id` | **Missing**; same logical resource in another TG account becomes another file row rather than another source of one Resource |
| Catalog | `repositories/files.py` | Partial; file listing and filename search exist, but no Resource/Catalog service layer |
| Classification | `repositories/categories.py`, `admin/api.py` | Implemented as one `files.category_id` foreign key; admin CRUD and assignment exist |
| Search | `FileRepository.search()` | Partial; filename-only PostgreSQL `ILIKE`, no category/resource-oriented search model |
| Download | `app/files/api.py`, `app/telegram/downloader.py` | Implemented, but file API directly constructs Telegram downloader and selects the fixed `account_id` from the file row |
| Streaming | `app/files/api.py`, `app/files/stream_service.py` | Implemented with HTTP Range and 4 MiB application cache chunks |
| Download source selection | `get_client(row["account_id"])` | **Missing failover/selection**; no alternate Telegram account is tried when the selected account is unavailable |
| Proxy boundary | `app/plugins/runtime.py`, external `plugins/proxy/` | Good direction; Core asks for `telegram.proxy` capability and can fall back to direct |
| Proxy deployment policy | config/plugin | Current code is deployment-oriented; account-scoped proxy is not a product requirement |
| Web auth | `app/auth/*` | Implemented and tested; remains cross-cutting, not a core domain |
| Admin | `app/admin/api.py`, `app/telegram/api.py` | Partial management surface; category and source operations exist, account management is incomplete |

## Current data model vs target model

Current schema contains:

```text
accounts
    |
    +-- telegram_sources
    |
    +-- files
           |
           +-- category_id -> categories
```

Current `files` rows represent a Telegram message/file location. The unique index is `(account_id, telegram_chat_id, message_id)`. This is correct for physical-source identity but insufficient for the product requirement that multiple Telegram accounts can back up one logical resource.

Target conceptual model:

```text
telegram_accounts
       |
       +---- telegram_messages / file_locations ----+
                                                    |
                                                    v
                                                resources
                                                    |
                                      +-------------+-------------+
                                      |                           |
                                      v                           v
                                  categories                 search index
```

The first implementation of this model does not require a generic storage abstraction. It requires a logical `Resource` above Telegram message/file locations.

## Telegram accounts: purpose and lifecycle

Multiple Telegram accounts serve two product purposes:

1. **Availability / redundancy** — a logical Resource may have more than one Telegram-backed copy/location so that a single account restriction does not make the Resource unavailable.
2. **Delivery optimization** — when multiple usable locations exist, Delivery may later choose the better path based on availability/health/throughput.

Therefore an account is an infrastructure/access identity, not a separate storage backend and not Web Auth.

A future Delivery source selector should be able to evaluate:

```text
Resource
  -> candidate Telegram locations
  -> account health / authorization
  -> connectivity health
  -> choose source
  -> download
  -> retry/fail over when safe
```

## Proxy plugin boundary

Proxy is optional deployment infrastructure.

```text
Telegram client boundary
          |
          v
     Connectivity
          |
     +----+----+
     |         |
  Direct    Proxy plugin
```

Core must not contain country/region detection or concrete proxy protocol logic. An administrator/deployment chooses direct vs proxy according to the server/network environment. The proxy implementation lives outside the core and is discovered through the plugin runtime. `PluginRuntime` loads external plugins from configured directories and exposes capabilities; the Telegram client asks for `telegram.proxy` and otherwise uses direct connectivity.

The product requirement does **not** require account-scoped proxy selection. Keep that out of the core model unless a real deployment requirement appears.

## Web authentication boundary

Web Auth is intentionally small and isolated:

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
      +---- user -> file APIs
      |
      +---- admin -> management APIs
```

It must not own Telegram sessions, Resources, Categories or download selection.

## Known gaps and bugs from the current code mapping

### P0 — logical Resource model is missing

The current database identifies each physical Telegram message/file location by `(account_id, telegram_chat_id, message_id)`. There is no logical Resource entity. Consequently, the same content copied to two Telegram accounts cannot be represented as two backing locations of one resource. This blocks the intended account-redundancy design and makes failover impossible at the domain level.

### P0 — account redundancy is defeated by account deletion semantics

`files.account_id` has `ON DELETE CASCADE`. Deleting an account therefore deletes all indexed file rows belonging to it, which is unsafe for a system whose accounts exist partly for redundancy. Account disable/removal must be separated from physical-resource metadata retention.

### P1 — Delivery is hard-wired to one Telegram account

Both download and stream resolve `get_client(row["account_id"])`. There is no source selector, health check or fallback to another Telegram-backed location. A restricted/broken account can therefore make an otherwise backed-up resource unavailable.

### P1 — scanner is doing domain work inside Telegram infrastructure

`app/telegram/scanner.py` directly writes `files` through `FileRepository`. It handles source filtering, message iteration, filename normalization, full-sync reconciliation and scan state in one Telegram-specific function. There is no separate recognition/resource-identification layer.

### P1 — catalog/search is too physical-file-oriented

`FileRepository.search()` searches only `filename ILIKE`, and list/search return physical Telegram identifiers. Category is a single nullable `files.category_id`, not a Resource-level classification model. This is sufficient for the current demo but not for the intended catalog-first product.

### P1 — Telegram account lifecycle is incomplete

`get_clients()` auto-discovers every `.session` file and creates clients, while `ApplicationLifecycle` then connects and scans every loaded client. The database `accounts.enabled` flag is not consulted when building the client set or starting scanners. There is also no admin API in the current Telegram API for enabling/disabling/removing accounts; it currently exposes account listing, dialog discovery and source creation.

### P1 — proxy runtime reload is only registry-level

`PluginRuntime.refresh()` reloads the plugin registry, but `get_clients()` caches Telegram clients globally and captures the proxy when each client is created. Refreshing the plugin registry therefore does not change existing Telegram connections. This is acceptable as an explicit lifecycle boundary, but the deployment must have a controlled reconnect/reload operation before claiming runtime proxy reconfiguration.

### P2 — top-level `telegram` package remains collision-prone

The application uses a top-level package named `telegram`, which has previously collided with unrelated Python packages. The current test bootstrap mitigates the problem, but the application package namespace remains fragile. Treat this as a refactor/packaging concern rather than a core domain requirement.

### P2 — download transport remains variable

The real-server benchmark showed large throughput variance, including a very slow middle-range request. HTTP Range semantics are currently implemented correctly, but transport bottlenecks have not been isolated. The next optimization must consider Resource source selection and redundancy rather than tuning a single fixed account path in isolation.

## Out of scope / intentionally rejected

- Generic storage-provider abstraction.
- Generic media-plugin architecture unless the product explicitly requires it later.
- Country/region logic embedded in application code.
- Account-scoped proxy policy as a default requirement.
- Treating Web users and Telegram accounts as one authentication model.

## Work order

1. Introduce the logical Resource + Telegram backing-location model.
2. Move recognition/normalization/deduplication behind an ingestion service.
3. Move category/search behavior to Resource/Catalog semantics.
4. Add Telegram account lifecycle management and health state.
5. Add Delivery source selection/failover using multiple Telegram locations.
6. Finish deployment-level proxy configuration/reconnect semantics.
7. Optimize transport only after the Resource/Delivery model can select among valid Telegram paths.
8. Keep Web Auth isolated and stable unless a concrete security defect is found.
