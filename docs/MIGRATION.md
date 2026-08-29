# TGDrive Migration / Architecture Convergence Record

Updated after the architecture reset and code mapping on 2026-08-30.

## Product definition

tgdrive is a **Telegram-only** file catalog and delivery system.

The intended product flow is:

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

Authentication is a cross-cutting boundary around Web/API access and is not a core domain.

## Architectural principle

> **Telegram Message is the physical source record; Resource is the system-recognized business entity; Category organizes Resources; Delivery consumes a Resource; Telegram Account is an access/redundancy path; Proxy is a Telegram connectivity policy; User/Admin Auth controls who may use or manage the system.**

Multiple Telegram accounts are used primarily for resource redundancy when one account is restricted, and secondarily as possible alternative download paths for delivery optimization. They are not separate storage providers.

## Current implementation mapping

### 1. Telegram access and accounts — implemented, but lifecycle incomplete

Current code:

- `app/telegram/client.py`
- `app/telegram/login.py`
- `repositories/accounts.py`
- `app/telegram/api.py`

Session files are discovered and synchronized into `accounts`; Telegram clients are created from those sessions. Dialog discovery and source creation are exposed to administrators.

Gap: `accounts.enabled` is not respected when `get_clients()` builds the client set or when lifecycle starts scanners. There is also no complete admin enable/disable/remove account API.

### 2. Source configuration — implemented

Current source identity is `(account_id, telegram_chat_id)`. The API validates the account and the database has a unique index for the pair.

This is the correct physical source boundary. Display names are not used as identifiers.

### 3. System recognition / ingestion — partially implemented

Current code:

- `app/telegram/scanner.py`
- `repositories/files.py`
- `repositories/sources.py`

The scanner selects configured chats, reads Telegram messages, extracts filename/size/MIME/date and writes directly to `files`. Incremental and full-sync safety behavior is present.

Architectural gap: the scanner currently owns both Telegram transport concerns and domain recognition/persistence. There is no distinct ingestion service, metadata normalizer, logical-resource identification or deduplication layer.

### 4. Resource model — missing

Current `files` rows are physical Telegram file/message locations and are uniquely identified by `(account_id, telegram_chat_id, message_id)`.

Target:

```text
Resource
  |
  +-- Telegram file location A
  +-- Telegram file location B
  +-- Telegram file location C
```

This is the most important architectural gap. Without a logical Resource entity, two copies of the same resource on different Telegram accounts cannot be linked, and Delivery cannot fail over between them.

### 5. Catalog / classification — partially implemented

Current code:

- `repositories/categories.py`
- `app/admin/api.py`
- `repositories/files.py`

Category CRUD and file-to-category assignment already exist. The previous documentation was stale when it described category management as incomplete.

The current limitation is the data model: `files.category_id` attaches classification to a physical file row rather than a logical Resource. Search also operates directly on physical files and currently uses filename-only `ILIKE`.

### 6. Delivery — implemented, but source selection is missing

Current code:

- `app/files/api.py`
- `app/files/range.py`
- `app/files/stream_service.py`
- `app/telegram/downloader.py`

Download and stream endpoints enforce Web authentication, availability and HTTP Range semantics. Telegram transport uses a 512 KiB request size while video caching uses 4 MiB application chunks.

The key architectural limitation is that both download and stream resolve the single `account_id` stored on the physical file row. There is no Resource-level source selector, health check, fallback or retry across backed-up Telegram locations.

### 7. Connectivity / proxy — good boundary, runtime reload incomplete

Current code:

- `app/plugins/interface.py`
- `app/plugins/runtime.py`
- external `plugins/proxy/`
- `app/telegram/client.py`

The Core asks the generic plugin runtime for the `telegram.proxy` capability and otherwise uses direct Telegram connectivity. Concrete proxy implementations remain outside Core.

Correct product rule: whether proxy is enabled is deployment/server-network configuration. Core must not infer proxy requirements from country or region. Account-scoped proxy selection is not required.

Gap: plugin registry refresh does not replace already-created Telegram clients. A proxy configuration change therefore requires explicit client reconnect/recreation.

### 8. Web authentication — implemented and intentionally low priority

Current code:

- `app/auth/*`

Web users authenticate through the signed HttpOnly session flow and admin APIs use the admin role. File APIs require an authenticated user. This is a cross-cutting access-control layer and should remain isolated from Telegram Resource logic.

## Critical findings

### P0 — no logical Resource entity

This blocks the most important multi-account requirement: preserving one logical resource across multiple Telegram-backed copies. The current physical uniqueness key is correct for Telegram message identity but insufficient for resource identity.

### P0 — account deletion can delete physical metadata needed for redundancy

`files.account_id` references `accounts(id) ON DELETE CASCADE`. Deleting a Telegram account therefore deletes its indexed file rows. Account lifecycle must distinguish disabling/removing an account from deleting resource/location metadata.

### P1 — download/stream cannot fail over

The current Delivery path is bound to `row["account_id"]`. If that Telegram account is restricted or unavailable, a backed-up copy on another account cannot be selected.

### P1 — recognition logic is trapped in Telegram scanner

Scanner directly writes the physical `files` table and combines discovery, normalization, reconciliation and persistence. Introduce an ingestion boundary before expanding recognition rules.

### P1 — catalog is not Resource-centric

Categories are attached to physical files and search is filename-only. The target is Resource-level classification and search metadata.

### P1 — account enabled state is not operationally enforced

The database has an `enabled` field, but client creation and scanner startup currently enumerate discovered sessions without filtering that field. Admin account lifecycle is incomplete.

### P1 — proxy reload does not update existing Telegram clients

`PluginRuntime.refresh()` changes the plugin registry, while Telegram clients retain the proxy captured during construction. Runtime proxy changes therefore require explicit reconnect/rebuild semantics.

### P2 — top-level `telegram` package namespace remains fragile

The application package name can collide with unrelated third-party packages. This is a packaging/refactor concern and should not distort the domain architecture.

### P2 — download throughput remains variable

The real-server benchmark showed severe variance for some Telegram ranges. Transport optimization remains open, but it should be addressed after Resource/source selection is modeled so that direct/proxied and redundant paths can be compared correctly.

## Existing issue reset

The previous GitHub issues were closed as completed, superseded, or out of scope. GitHub's available repository integration does not expose issue deletion, so the historical issues remain in closed state rather than being physically deleted.

The active work should now be represented by the new issue set created from this code mapping.

## Migration order

1. Add logical `Resource` and Telegram backing-location model without introducing a generic storage-provider abstraction.
2. Add ingestion/recognition boundaries and deterministic resource identification/deduplication.
3. Move classification/search semantics from physical file rows to Resources.
4. Correct Telegram account lifecycle and health state.
5. Add Delivery source selection and safe failover across Telegram accounts.
6. Finish deployment-level proxy configuration and explicit reconnect/reload behavior.
7. Profile and optimize download transport across valid Telegram paths.
8. Keep Web Auth stable unless a concrete security defect is discovered.

## Completion definition for this migration phase

The architecture migration is complete when the code and documentation agree on the same model:

- Telegram is the only backend.
- Ingestion/recognition and Catalog are the primary domains.
- Resource is distinct from Telegram message/file location.
- Multiple Telegram accounts provide redundancy/alternative delivery paths.
- Proxy is an optional external connectivity plugin selected by deployment configuration.
- Auth is a cross-cutting access-control layer.
- Issues reflect verified current gaps rather than historical, already-fixed work.
