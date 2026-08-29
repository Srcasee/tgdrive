# Phase 2 — High-Speed Download Transport

## Status

**Paused by design.** The first real-server benchmark is complete, but transport optimization is not. Do not spend implementation effort on parallel chunking or a video-player simulation until the setup/runtime cleanup is complete.

## Validated baseline

The Telegram-backed streaming path is functionally correct:

- Complete small-file download works.
- HTTP Range returns `206 Partial Content`.
- `Content-Range` and response lengths are correct.
- Telegram authentication, source scanning and file indexing work through the real proxy-enabled deployment.

A 276,027,608-byte MP4 showed highly variable throughput, including a very slow middle-of-file range. The raw baseline remains in `docs/MIGRATION.md` and Issue #13.

## When resumed

1. Build a repeatable benchmark matrix for offset, range size, cache state and proxy/direct mode.
2. Measure TTFB, sustained throughput, CPU, memory, retries and Telegram request behavior.
3. Determine whether Telethon request sizing or single-connection serialization is material.
4. Only then evaluate bounded parallel retrieval and ordered reassembly.
5. Preserve HTTP Range semantics and authorization.
6. Run realistic browser/video-player simulation only as the final validation.

## Non-goals

- No claim of bypassing Telegram service-side limits.
- No arbitrary high concurrency.
- No media-plugin-specific Telegram download implementation.
