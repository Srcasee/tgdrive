# Project Status and Target Alignment

Updated 2026-08-30 after the Resource, Ingestion, Catalog, and legacy-logic cleanup work.

## Product definition

tgdrive is a **Telegram-only** file catalog and delivery system.

The primary product flow is:

```text
Telegram storage
      |
      v
System recognition / ingestion
      |
      v
Logical Resource
      |
      v
Catalog + classification + search
      |
      v
Download / streaming
```

No generic storage-provider abstraction is required or planned.

## Domain priorities

1. Ingestion / system recognition.
2. Logical Resource identity.
3. Catalog / classification / search.
4. Delivery / download / streaming with Telegram source failover.
5. Telegram account redundancy and alternative delivery paths.
6. Deployment connectivity / optional proxy plugin.
7. Web authentication / authorization as a cross-cutting concern.

## Current implementation status

### Telegram discovery

- Telegram session discovery and account synchronization: implemented.
- Explicit source configuration by account + Telegram chat ID: implemented.
- Incremental scanning: implemented.
- Full-sync failure-safe reconciliation: implemented.
- Scanner failure state: implemented.
- Scanner traversal is metadata-only and does not download file payloads.

### Ingestion

- Telegram message recognition and metadata normalization: implemented.
- `TelegramFileObservation` boundary: implemented.
- Resource identification/persistence: implemented.
- Physical Telegram locations remain separate from logical Resources: implemented.
- Content SHA-256 utility: implemented as an explicit streaming operation only.
- Scanner does not calculate content hashes by downloading files.

Content verification must happen only when a full byte stream is explicitly consumed. A partial HTTP Range cannot establish a full-file content identity.

### Logical Resource

The data model now separates:

```text
Resource
   +-- Telegram file location A
   +-- Telegram file location B
   +-- Telegram file location C
```

`files.resource_id` identifies the logical Resource while `(account_id, telegram_chat_id, message_id)` identifies a physical Telegram location.

Account deletion no longer deletes physical file metadata: `files.account_id` uses `ON DELETE SET NULL`.

### Catalog

- Resource-centric listing: implemented.
- Resource-centric filename search: implemented.
- Resource categories via `resource_categories`: implemented.
- Category filtering: implemented.
- Resource detail with source count: implemented.
- Admin Resource-to-category assignment: implemented.
- Legacy `files.category_id` removed from the live schema.

### Delivery

- Telegram source selection by logical Resource: implemented.
- Basic source failover during streaming/download: implemented.
- HTTP Range handling: implemented.
- Video chunk streaming/cache: implemented.

Delivery should select among available physical Telegram locations rather than treating one account as the Resource owner.

### Telegram accounts

Multiple Telegram accounts are used as redundant physical access paths.

Primary purpose:

- prevent one restricted account from invalidating a Resource.

Secondary purpose:

- provide alternative delivery paths for performance optimization.

They are not separate storage providers.

### Proxy / connectivity

- Generic plugin runtime: implemented.
- External proxy plugin boundary: implemented.
- Direct connection fallback: implemented.
- Deployment-controlled proxy enablement: supported.
- Account-scoped proxy policy is not a product requirement.

### Web Auth

- User/admin authentication: implemented.
- Signed expiring HttpOnly session: implemented.
- Protected user endpoints: implemented.
- Admin authorization: implemented.

Auth remains a cross-cutting concern and is not part of the main content pipeline.

## Legacy cleanup

The active code path no longer retains compatibility wrappers for the pre-Resource model.

Removed:

- `FileRepository.upsert_verified_message` compatibility wrapper.
- `hash_telegram_file` compatibility helper.
- file-level category repository/list/search semantics.
- live `files.category_id` schema column.
- unused `shares` table.

Historical migration steps remain in `database.py` only so existing deployments can upgrade safely; they are not part of the active domain model.

## Current data model

```text
accounts
    |
    +-- telegram_sources
    |
    +-- files ----> resources ----> resource_categories ----> categories
          |
          +-- physical Telegram location
```

The important identity boundary is:

```text
Physical location = account + chat + message
Logical Resource  = system-level content entity
```

Content SHA-256 is the strongest verified identity, but it is intentionally not computed during metadata-only scanning.

## Remaining gaps

### P1 — content identity promotion

A full, explicitly requested byte stream can produce a verified SHA-256, but the delivery path does not yet promote that verified hash into a canonical Resource merge workflow. This should be implemented without writing the payload to disk.

### P1 — Catalog search depth

Catalog search is currently filename-based. Rich metadata/full-text search can be added after the Resource identity boundary is stable.

### P1 — account lifecycle/health

Account enable/disable and runtime health are not yet a complete policy-driven subsystem.

### P1 — delivery source policy

Failover exists, but source selection is still basic ordering. Health, latency and failure scoring can later improve path selection.

### P1 — proxy live reload

Changing the proxy plugin registry does not automatically recreate existing Telegram clients. A controlled reconnect/rebuild operation is required.

### P2 — Telegram package namespace

The internal top-level `telegram` package name can collide with unrelated third-party packages. This remains a packaging concern, not a reason to add a generic storage abstraction.

### P2 — download throughput

Real-server measurements show substantial Telegram Range variance. Optimization should happen after Resource source selection and health policy are stable.

## Target architecture

```text
                         +------------------+
                         |    Web User      |
                         +--------+---------+
                                  |
                           Search / Browse
                                  |
                                  v
                       +----------------------+
                       |       Catalog        |
                       | Resource / Category  |
                       | Search / metadata    |
                       +----------+-----------+
                                  ^
                                  |
                           Logical Resource
                                  ^
                                  |
                       +----------+-----------+
                       |      Ingestion       |
                       | Recognize / Normalize|
                       | Identify / Persist   |
                       +----------+-----------+
                                  ^
                                  |
                           Telegram metadata
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

Download path:

Resource
   |
   v
available Telegram locations
   |
   v
source selection / failover
   |
   v
Telegram bytes -> user
```

## Work order

1. Complete verified content-hash promotion/merge without scan-time downloads.
2. Complete Resource-centric Catalog search and browse semantics.
3. Complete Telegram account lifecycle and health policy.
4. Improve Delivery source scoring/failover.
5. Finish deployment-level proxy reconnect/reload semantics.
6. Profile and optimize download transport across valid Telegram paths.
7. Keep Auth stable unless a concrete security defect is found.

## Explicit non-goals

- Generic storage-provider abstraction.
- Generic media-plugin architecture.
- Country/region detection in application logic.
- Account-scoped proxy policy as a default requirement.
- Treating Telegram accounts as Web Auth identities.
- Downloading Telegram payloads during ordinary indexing.
