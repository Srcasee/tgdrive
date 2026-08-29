# Phase 2 — High-Speed Download Transport

## Objective

Make tgdrive's own transport path as unconstrained as practical before deep proxy/plugin work. Telegram remains the content backend; this phase does not promise bypassing Telegram service-side limits.

## Phase 2 baseline: real-server benchmark

The first benchmark is complete. A real 276,027,608-byte MP4 was requested through the authenticated `/files/9/stream` endpoint using HTTP Range requests.

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

A JPG download also returned HTTP 200 with a valid JPEG, and an MP4 Range request returned HTTP 206 with the correct `Content-Range` and exact requested byte count.

### Interpretation

The HTTP layer is not the immediate functional blocker: Range requests, streaming, authentication and Telegram-backed retrieval all work. However, throughput is highly variable and can become extremely slow for a middle-of-file range. The current data is a baseline, not proof of one root cause.

The investigation must isolate:

- Telegram DC/network behavior for different offsets.
- SOCKS5/proxy path behavior.
- Telethon `iter_download` request sizing and serialization.
- Application cache hit/miss behavior.
- CPU/decryption overhead.
- Whether a single Telegram connection/request sequence is the dominant bottleneck.

## Current path

```text
Browser / curl
  -> FastAPI StreamingResponse
  -> TelegramDownloader
  -> Telethon iter_download
  -> Telegram DC / network / proxy
```

Video additionally uses `VideoStreamService` and an application cache chunk.

## First-round safeguards already completed

- Telegram transport request size is constrained to 512 KiB.
- Application-level video cache chunk size remains separate from Telegram request size.
- `cryptg` is installed for C-accelerated Telegram media decryption.
- HTTP Range behavior has been validated on the real server.
- A complete JPG download has been validated end-to-end.
- An MP4 partial range has been validated end-to-end.

## Next optimization stages

### 1. Controlled benchmark matrix — next

Repeat the benchmark with a fixed test file and controlled conditions:

- 1 / 8 / 32 / 128 MiB ranges.
- Beginning, middle and end offsets.
- Cold and repeated requests.
- Direct Telegram path where available.
- Proxied Telegram path.
- Single worker first, then bounded concurrency.
- TTFB, sustained MB/s, CPU, memory, request latency and error/retry rate.

The current real-server result must remain the regression baseline until a better result is reproduced consistently.

### 2. Download Manager

Introduce a Core `DownloadManager` that schedules transport chunks independently from HTTP response handling. Keep chunk scheduling and reassembly independent of proxy and media plugins.

### 3. Parallel range/chunk retrieval

Evaluate bounded concurrent Telegram requests and ordered reassembly. Concurrency must be adaptive/configurable rather than an arbitrary fixed high number. Only proceed when the controlled benchmark demonstrates that concurrency improves sustained throughput without unacceptable errors, CPU or memory use.

### 4. Shared cache

For repeated downloads, allow a local/object cache to absorb repeated Telegram reads. Cache policy must be independent of media type.

### 5. Multi-account / multi-route evaluation

Only after benchmark evidence supports it, evaluate account-scoped Telegram clients and independent proxy routes. This must respect Telegram service behavior and deployment constraints; multiple accounts are not assumed to multiply throughput automatically.

### 6. Real video-player simulation — final validation only

Per the project execution plan, browser/video-player simulation is intentionally deferred until transport optimization is complete. It should validate realistic seek, startup, buffering and sequential Range behavior after the transport baseline has been improved.

## Completion criteria

Phase 2 download optimization is **not complete** until:

1. The controlled benchmark matrix is repeatable.
2. A clear bottleneck is identified or the remaining limit is demonstrated to be outside tgdrive's control.
3. A bounded transport optimization is implemented where measurements justify it.
4. No regression is introduced to HTTP Range semantics or file authorization.
5. Sustained throughput improves materially over the current baseline, or a documented external/network ceiling is established.
6. Final browser/video-player simulation passes after transport work is frozen.

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
