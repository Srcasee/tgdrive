# TGDrive Migration / Real-Server Validation Record

This document records the staged migration from Core-only validation to a real Telegram-backed deployment.

## Baseline validated on 2026-08-29

The Debian 12 deployment successfully reached the following state:

- PostgreSQL 16 is healthy.
- Core starts normally.
- `default.session` is available to the Core container.
- Telegram account `default` is authorized.
- Telegram dialogs can be queried through the API.
- A source is explicitly configured by `account_id` + `telegram_chat_id`.
- The source scanner completed successfully and indexed 9 files.
- File listing/search APIs return the indexed metadata.
- Complete JPG download returns a valid JPEG.
- MP4 Range streaming returns HTTP 206 with correct `Content-Range` semantics.
- SOCKS5 proxy connectivity and Telethon authorization were validated.

## Important source-selection rule

Telegram dialog names are presentation metadata and are not unique identifiers. A deployment can legitimately contain multiple dialogs named `My Documents` with different chat IDs. Only rows explicitly configured in `telegram_sources` are scanned.

For example, the validated source was:

```text
account_id       = 1
telegram_chat_id = -1004413553797
name             = My Documents
```

A second dialog with the same display name but another chat ID is not implicitly included by this source configuration.

## Migration sequence

### 1. Runtime and database

- Verify the target Python runtime is compatible; do not replace the operating system Python solely for TGDrive.
- Start PostgreSQL.
- Start Core.
- Verify database initialization and HTTP startup.

### 2. Proxy, if required

- Verify the proxy container independently.
- From the Core container, test SOCKS5 TCP connectivity to Telegram.
- Test TLS through the proxy.
- Resolve the TGDrive proxy plugin and verify the resulting Telethon proxy configuration.
- Only then enable Telegram runtime through the proxy.

### 3. Telegram account

- Place the authorized Telethon session under the configured account session directory.
- Start Core and confirm an authorized account in the logs.
- Query `/api/telegram/accounts`.
- Query `/api/telegram/accounts/{account_id}/dialogs`.

### 4. Source configuration

- Choose the exact Telegram chat ID from dialog discovery.
- Create one `telegram_sources` row.
- Confirm the database uniqueness constraint prevents accidental duplicates.
- Do not configure sources by display name alone.

### 5. Scan and verify

- Let the scanner run.
- Confirm `scan_status=success`.
- Confirm `last_message_id` advances.
- Compare the scanner log with the configured chat ID.
- Confirm the expected file count and metadata in PostgreSQL.

### 6. File transport

Verify in this order:

1. File listing.
2. Filename search.
3. Complete small-file download.
4. MP4 Range request.
5. Only after those pass, run performance measurements.

## Performance migration status

The first real-server benchmark is complete, but transport optimization is not.

A 276,027,608-byte MP4 produced these results:

| Range | Time | Throughput |
|---|---:|---:|
| 0–1 MiB | 6.60 s | 0.16 MB/s |
| 0–8 MiB | 4.23 s | 1.98 MB/s |
| 128–136 MiB | 149.57 s | 0.056 MB/s |
| 64–72 MiB, repeated #1 | 10.45 s | 0.80 MB/s |
| 64–72 MiB, repeated #2 | 9.19 s | 0.91 MB/s |
| 64–72 MiB, repeated #3 | 9.49 s | 0.88 MB/s |
| 64–72 MiB, repeated #4 | 10.25 s | 0.82 MB/s |
| 64–72 MiB, repeated #5 | 10.85 s | 0.77 MB/s |

The result establishes a reproducible starting point but does not identify a unique bottleneck. Next migration work must isolate direct vs proxy behavior, Telegram offset behavior, cache state, Telethon request sizing, CPU/decryption cost and single-connection serialization before implementing parallel chunk retrieval.

## Execution order constraint

Realistic browser/video-player simulation is intentionally the final validation step. It should not be used to hide transport-layer performance problems or become the first diagnostic tool.

## Completion definition

The migration baseline is complete when the real server can authenticate to Telegram, scan an explicitly selected source, index files, and serve complete and Range-based file access. That baseline is now achieved.

Phase 2 download optimization remains open until controlled benchmarks identify the bottleneck and a justified transport optimization improves sustained throughput without breaking Range semantics, authorization, or resource limits.
