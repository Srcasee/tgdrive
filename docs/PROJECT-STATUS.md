# Project Status and Target Alignment

Updated 2026-08-30 after the architecture reset and repository-wide code mapping.

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
Resource catalog + classification
      |
      +----> Web search / browse
      |
      +----> Download / streaming
```

No generic storage-provider abstraction is required or planned.

## Domain priorities

1. Ingestion / system recognition.
2. Catalog / classification / search.
3. Delivery / download / streaming.
4. Telegram account redundancy and alternative delivery paths.
5. Deployment connectivity / optional proxy plugin.
6. Web authentication / authorization as a cross-cutting concern.

## Current implementation status

### Telegram ingestion

- Telegram session discovery and account synchronization: implemented.
- Real Telegram authorization: validated on the deployment server.
- Explicit source configuration by account + Telegram chat ID: implemented.
- Incremental scanning: implemented.
- Full-sync failure-safe reconciliation: implemented.
- Scanner failure state: implemented.

### Catalog

- File metadata persistence: implemented.
- Filename search: implemented.
- Category persistence: implemented.
- Category CRUD and file-to-category assignment: implemented.

However, the logical `Resource` model is not implemented. Current rows are physical Telegram message/file locations. Search and classification therefore remain physical-file-oriented.

### Delivery

- Authenticated file listing: implemented.
- Filename search: implemented.
- Complete download: implemented and real-server validated.
- HTTP Range: implemented with 416 handling, suffix and open-ended ranges.
- Video streaming: implemented with application-level cache/prefetch.

The Delivery path currently uses the one `account_id` stored on each physical file row. There is no Resource-level source selection or failover across Telegram accounts.

### Telegram accounts

Multiple accounts are currently loaded from session files and synchronized to the `accounts` table.

Product intent:

- primary purpose: redundancy so one restricted account does not invalidate a resource;
- secondary purpose: provide alternative download paths for delivery optimization.

Current implementation does not model multiple Telegram locations as copies of one logical Resource, and account lifecycle controls are incomplete.

### Proxy / connectivity

- Generic plugin runtime: implemented.
- External proxy plugin boundary: implemented.
- Direct connection fallback: implemented.
- Deployment-controlled proxy enablement: supported.
- Real SOCKS5 connectivity and Telegram authorization: validated.

Runtime registry refresh does not recreate already-instantiated Telegram clients, so proxy changes require an explicit reconnect/rebuild operation. Account-scoped proxy policy is not a product requirement.

### Web Auth

- User/admin authentication: implemented.
- Signed expiring HttpOnly session: implemented.
- Protected file endpoints: implemented.
- Admin authorization: implemented.

Auth is intentionally treated as a cross-cutting layer rather than the product's domain center.

## Current data model

```text
accounts
    |
    +-- telegram_sources
    |
    +-- files ----> categories
```

`files` is currently uniquely identified by `(account_id, telegram_chat_id, message_id)`. This correctly identifies a physical Telegram message/file location but cannot express:

```text
Resource #123
   +-- TG Account A / message X
   +-- TG Account B / message Y
```

That logical relationship is the highest-priority missing domain model.

## Verified gaps / bugs

### P0 — logical Resource model missing

No logical Resource entity exists above physical Telegram file/message rows. This prevents cross-account backup relationships and source failover.

### P0 — account deletion cascades physical file metadata

`files.account_id` uses `ON DELETE CASCADE`. Deleting an account deletes its indexed file rows, which conflicts with the requirement to preserve resource metadata and redundancy across account failures/removal.

### P1 — Delivery is bound to one physical account

Download and stream resolve the Telegram client from the physical row's `account_id`. No alternate backed-up Telegram location can be selected.

### P1 — ingestion/recognition is not a distinct domain service

The Telegram scanner performs Telegram traversal, metadata extraction, normalization, reconciliation and direct persistence in one module. Recognition and deduplication need an explicit boundary.

### P1 — Catalog is physical-file-centric

Search is filename-only `ILIKE`; category is a nullable foreign key on `files`. Resource-level classification and richer search semantics are not yet modeled.

### P1 — account enabled flag is not enforced by runtime startup

The database contains `accounts.enabled`, but the current client discovery and scanner startup paths do not filter clients by this flag. Admin account lifecycle operations are also incomplete.

### P1 — proxy reload is not a live client reconfiguration

Plugin refresh changes the registry but existing Telegram clients retain their original proxy. A controlled reconnect/rebuild operation is required for runtime proxy changes.

### P2 — top-level `telegram` package namespace is fragile

The internal package name can collide with unrelated third-party packages. Keep this as a packaging/refactor concern, not a reason to introduce a generic Telegram abstraction.

### P2 — download throughput remains variable

The real-server benchmark showed substantial variance for Telegram ranges, including a very slow middle-range request. Optimization should follow Resource source selection so multiple valid Telegram paths can be measured before adding concurrency.

## Real-server baseline

The 2026-08-29 deployment validated PostgreSQL health, Telegram authorization, dialog discovery, configured source scanning, indexed file search/listing, JPG download, MP4 Range streaming, and SOCKS5 proxy connectivity.

The real-server benchmark for a 276,027,608-byte MP4 remains the baseline:

| Test | Result |
|---|---:|
| 1 MiB range, first bytes | 6.60 s / 0.16 MB/s |
| 8 MiB range, first bytes | 4.23 s / 1.98 MB/s |
| 8 MiB range, middle | 149.57 s / 0.056 MB/s |
| 8 MiB range, repeated #1 | 10.45 s / 0.80 MB/s |
| 8 MiB range, repeated #2 | 9.19 s / 0.91 MB/s |
| 8 MiB range, repeated #3 | 9.49 s / 0.88 MB/s |
| 8 MiB range, repeated #4 | 10.25 s / 0.82 MB/s |
| 8 MiB range, repeated #5 | 10.85 s / 0.77 MB/s |

## Target architecture

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
                       | Scanner / Parser     |
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

## Work order

1. Introduce logical Resource + Telegram backing-location model.
2. Separate recognition/normalization/deduplication from Telegram transport.
3. Make Catalog classification/search Resource-centric.
4. Correct Telegram account lifecycle and health state.
5. Add Delivery source selection and safe failover.
6. Finish deployment-level proxy reconnect/reload semantics.
7. Profile and optimize download transport across valid Telegram paths.
8. Keep Auth stable unless a concrete security defect is found.

## Explicit non-goals

- Generic storage-provider abstraction.
- Generic media-plugin architecture.
- Country/region detection in application logic.
- Account-scoped proxy policy as a default requirement.
- Treating Telegram accounts as Web Auth identities.
