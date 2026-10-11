# Project Complete Call Chain

## Overview

This document describes the current runtime flow of tgdrive from deployment, Telegram authorization, dialog discovery, Source configuration, scanning, ingestion, downloading, and delivery.

## 1. Deployment and Application Startup

```text
./deploy.sh
    |
    v
Container startup
    |
    v
app/main.py
    |
    v
app/core/lifecycle.py
```

`ApplicationLifecycle` is application orchestration only:

- initialize PostgreSQL connection pool
- initialize database schema
- bootstrap admin account
- start and stop runtime components

Core does not contain Telegram business logic.

## 2. Telegram Login and Runtime

First-time authorization:

```text
telegram/login.py
        |
        v
telegram/client.py
        |
        v
Telegram session creation
```

`login.py` is only used for initial account authorization. Normal startup reuses existing sessions.

Runtime:

```text
ApplicationLifecycle
        |
        v
telegram/client.py
        |
        v
Existing Telegram sessions
```

## 3. Dialog Discovery Flow

Dialog Discovery maintains the Telegram dialog metadata cache.

```text
Telegram Client
        |
        v
telegram/dialog_discovery.py
        |
        v
Telegram dialogs
        |
        v
dialog repository
        |
        v
dialogs table
```

Current behavior:

- Runtime reconciliation can refresh dialogs.
- The Admin Dialog view reads cached dialog data.
- First Admin Dialog access may lazily initialize discovery when no dialog cache exists.
- After initialization, normal page refreshes only read the dialogs table.
- Explicit reconciliation remains the manual discovery trigger.

Dialog Discovery does not create Sources and does not start Scanner.

## 4. Dialog and Source Boundary

Dialog and Source are separate domains.

```text
Dialog Discovery
        |
        v
dialogs table

Admin selects dialog
        |
        v
Source configuration
        |
        v
sources table
```

A Source represents an administrator-selected Telegram resource that Scanner is allowed to process.

## 5. Source Scanner Flow

```text
SourceRepository
        |
        v
ScannerManager
        |
        v
telegram/scanner.py
        |
        v
Telegram message API
        |
        v
File message processing
```

Scanner responsibilities:

- read enabled Sources
- scan Telegram messages
- extract file metadata
- submit resources to catalog/ingestion

Scanner does not perform Dialog Discovery.

Current Source change behavior:

- Source changes wake Scanner immediately.
- Scanner currently performs a full enabled Source scan for correctness.
- Incremental Source scanning is deferred.

## 6. Catalog and Ingestion Flow

```text
scanner.py
    |
    v
Catalog layer
    |
    v
Ingestion layer
    |
    v
Resource metadata and state management
```

## 7. Resource Download / HTTP Delivery Call Chain

The current public download API is Resource-scoped. It streams bytes from Telegram through the server; it does not first download the complete file to local disk.

```text
GET /resources/{resource_id}/download
  or GET /resources/{resource_id}/stream
  or GET /share/{token}
        |
        v
app/download/api.py
  download_resource() / stream_resource() / shared_download()
        |
        v
_stream_response()
  - _resource(): checks active/available Resource
  - parses a single HTTP Range and sets Content-Length / Content-Range / ETag
  - DownloadService.start()
        |
        v
TelegramSourceSelector.stream_resource()
app/download/source_selector.py
  - candidates() -> TelegramFileRepository.list_resource_sources()
  - restricts candidates to the same telegram_chat_id + message_id
  - resolves an account session and checks Telegram message metadata/size
  - resumes at the current byte offset after a source fails
  - waits failover_delay (default 15 seconds) before trying the next candidate
        |
        v
TelegramDownloader.get_file_info() / stream()
app/download/downloader.py
  - client.get_messages(chat_id, ids=message_id)
  - client.iter_download(media, offset, chunk_size, request_size)
  - emits byte chunks; request size is capped at 512 KiB
        |
        v
DownloadService.stream() -> _limited_stream()
app/download/service.py
  - applies TGDRIVE_MAX_CONCURRENT_DOWNLOADS (default 8)
  - records queue wait and active transfer state
        |
        v
tracked_stream()
app/download/transfer.py
  - counts bytes and checks expected length
  - records completed / failed / cancelled transfer state
        |
        v
FastAPI StreamingResponse
  app/download/api.py
        |
        v
HTTP client
```

### Download-related persistence and helpers

- `app/repositories/telegram_files.py — TelegramFileRepository.list_resource_sources()`: returns enabled accounts and enabled/available physical Telegram locations for a Resource.
- `app/repositories/accounts.py — AccountRepository.get_session()`: resolves the Telegram session name for a source account.
- `app/download/range.py — parse_single_range()`: parses a single HTTP byte range; invalid ranges become HTTP 416.
- `app/download/repository.py — DownloadRepository.create()/complete()/fail()`: persists transfer history/state through `DownloadService`.
- `app/repositories/resources.py — ResourceRepository.get()`: resolves the logical Resource metadata used by the HTTP response.
- `app/download/api.py — download_head()/stream_head()`: return metadata without streaming the file body.
- `app/download/api.py — create_share()` and `app/download/api.py — shared_download()`: create and serve a Resource share link.

The normal delivery path does not calculate a SHA-256 digest. An already recorded hash may be used for an ETag; otherwise `_resource_etag()` falls back to a stable Resource-ID-and-size validator.

The 15-second delay is triggered after a source raises an error or ends before the expected byte count. It is not a general 15-second no-data timeout: a stalled iterator that neither yields nor raises will not trigger failover by this delay alone.

## 8. Chat-level Download Feasibility

Current delivery endpoints accept one `resource_id` at a time. The catalog can filter/list Resources by `chat_id` (`app/catalog/api.py — list_resources()`; query logic in `app/catalog/repository.py — list_resources()`), but there is no Chat-level bulk-download endpoint or archive job in Core today.

A Chat-level download is feasible without changing Resource identity. A future implementation should:

1. Accept an explicit Telegram Chat/source scope and resolve its active, available Resources.
2. Deduplicate logical Resource IDs so the same Resource is not included twice just because multiple accounts expose it.
3. Download each Resource through the existing Resource delivery/source-selector path.
4. Package entries into a ZIP archive and stream it or provide a background archive job for large Chats.
5. Define deterministic filename-collision handling, cancellation/progress reporting, retry behavior, archive-size limits, and access control.
6. Bound parallel Resource downloads; do not equate the existing transfer semaphore with safe unlimited per-file parallelism.

For small Chats, a streamed ZIP can be enough. For large Chats, a background job plus temporary storage is more robust because ZIP finalization, retries, disconnects, and resumability are harder to manage in one HTTP stream. Ordinary Chat download should remain metadata-only until a user requests the archive; scanning must not download file payloads.

## 9. Deferred Work

### Download performance

Status: deferred; do not implement until the download-state behavior is reliable and measurements identify the bottleneck.

The future optimization outline is maintained in `docs/PHASE-2-DOWNLOAD.md`. It records only candidate directions, not an implementation plan or a commitment to optimize now.

### Chat-level bulk download

Status: feasible but not implemented. See section 8 above.

### Existing operational follow-ups

- Keep Source lifecycle changes and Dialog discovery responsibilities separate.
- Investigate download resume/completion/file-extraction state consistency before performance work.
