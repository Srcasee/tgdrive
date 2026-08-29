# Phase 2 — High-Speed Download Transport

## Objective

Make tgdrive's own transport path as unconstrained as practical before deep proxy/plugin work. Telegram remains the content backend; this phase does not promise bypassing Telegram service-side limits.

## Current path

```text
Browser
  -> FastAPI StreamingResponse
  -> TelegramDownloader
  -> Telethon iter_download
  -> Telegram DC / network / proxy
```

Video additionally uses `VideoStreamService` and a 4 MiB application cache chunk.

## First-round safeguards already completed

- Telegram transport request size is constrained to 512 KiB.
- Application-level video cache chunk size remains separate from Telegram request size.
- `cryptg` is installed for C-accelerated Telegram media decryption.

## Next optimization stages

### 1. Benchmark

Measure real throughput before changing concurrency:

- 10 MB / 100 MB / 1 GB / 5 GB files.
- Direct Telegram path.
- Each configured proxy path.
- Single worker and controlled parallel workers.
- TTFB, sustained MB/s, CPU, memory, request latency and error/retry rate.

### 2. Download Manager

Introduce a Core `DownloadManager` that schedules transport chunks independently from HTTP response handling. Keep chunk scheduling and reassembly independent of proxy and media plugins.

### 3. Parallel range/chunk retrieval

Evaluate bounded concurrent Telegram requests and ordered reassembly. Concurrency must be adaptive/configurable rather than an arbitrary fixed high number.

### 4. Shared cache

For repeated downloads, allow a local/object cache to absorb repeated Telegram reads. Cache policy must be independent of media type.

### 5. Multi-account / multi-route evaluation

Only after benchmark evidence supports it, evaluate account-scoped Telegram clients and independent proxy routes. This must respect Telegram service behavior and deployment constraints; multiple accounts are not assumed to multiply throughput automatically.

## Architectural boundary

```text
Core File Transport
  ├── DownloadManager
  ├── ChunkScheduler
  ├── Reassembler
  └── Cache
        |
        +--> Telegram client abstraction
        |
        +--> Proxy interface (optional)
        |
        +--> Media consumers (later)
```

Media plugins must consume the Core file transport and must not implement their own Telegram downloading path unless there is a documented, measured reason.
