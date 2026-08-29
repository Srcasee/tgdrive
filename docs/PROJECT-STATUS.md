# Project Status and Target Alignment

Updated after the first real-server Telegram integration and download transport benchmark on 2026-08-29.

## Current implemented capabilities

### Core ingestion and indexing

- Telegram session discovery and account synchronization.
- Real Telegram account authorization validated on the deployment server.
- Configured private Telegram source scanning.
- PostgreSQL file metadata/index.
- Incremental scanning plus hardened full-sync reconciliation.
- Explicit scanner failure state and failure-safe recovery.

### Web access

- Web authentication with user/admin roles.
- Expiring, signed HttpOnly web sessions.
- User authorization for file APIs.
- Admin-only Telegram account/source administration.
- File listing and filename search.
- Protected download and video stream endpoints.
- HTTP Range support with single-range/open-ended/suffix handling and 416 responses.
- Video streaming with application-level chunk cache/prefetch.

### Administration and Telegram integration

- Category persistence.
- Category CRUD API/UI.
- File-to-category assignment.
- Telegram source validation and uniqueness.
- Telegram session credentials are kept server-side and are not returned by account APIs.
- Real account/dialog discovery validated through the API.
- A configured source was scanned successfully and indexed 9 files.

### Infrastructure extensibility

- Proxy plugin interface and Python entry-point discovery.
- Independent SOCKS5 proxy plugin.
- Proxy selection is deployment configuration, not geographic logic embedded in Core.
- SOCKS5 TCP/TLS connectivity to Telegram's HTTPS endpoint was validated from the Core container.
- Telethon successfully connected and authorized through the configured proxy on the real deployment server.

## Current performance finding

The HTTP Range/streaming path is functionally working, but high-speed download optimization is **not complete**.

A real 276,027,608-byte MP4 was used for range tests through `/files/9/stream`:

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

The benchmark proves that Range responses and streaming work, but also shows severe and variable throughput for non-initial Telegram ranges. This is evidence for Phase 2 transport optimization, not evidence of a single root cause. Telegram, proxy/network path, Telethon request behavior, cache state, and single-range serialization still need to be isolated by controlled benchmarks.

A normal JPG download was also verified end-to-end: `/files/1/download` returned HTTP 200 and a valid 1800x2700 JPEG.

## Not yet implemented / not yet complete

- Production-grade runtime proxy hot-plug/reload.
- Account-scoped proxy selection and routing policy.
- High-speed Download Manager with parallel chunk scheduling/reassembly.
- Shared local/object cache for popular files.
- Controlled direct-vs-proxy transport benchmark matrix.
- Real video-player simulation and playback-behavior validation (intentionally deferred until the end).
- Image online viewer.
- Generic Media Plugin manager.
- Audio/media plugin implementations.

## Alignment with the original goal

The project is **functionally integrated end-to-end on the real deployment server**, but performance work remains open.

| Original goal | Current state | Alignment |
|---|---|---|
| Files uploaded to private TG groups are scanned/indexed | Implemented and real-server validated | Yes |
| Users search files on Web | Implemented | Yes |
| Users download files | Implemented and real-server validated | Yes |
| Admin classifies files | Implemented | Yes |
| Deploy in different regions | Supported by configuration/proxy plugin boundary | Yes |
| Proxy is hot-pluggable | Plugin discovery exists; production runtime hot-plug still needs hardening | Partial |
| Video playback | Streaming endpoint works; player simulation intentionally deferred | Partial |
| Image online browsing | Not implemented | Future |
| Other media features are extensible plugins | Generic media plugin boundary not implemented | Future |
| Download speed should not be unnecessarily limited by tgdrive | Range/stream transport works, but benchmark shows substantial throughput variance | Phase 2 open |

## Phase 1 status

**Phase 1 is considered complete for the current Core scope and real-server baseline.** The application authenticates to Telegram, discovers dialogs, accepts a configured source, scans it successfully, indexes files, and serves authenticated file download/stream requests. Existing GitHub issues that cover future hardening or broader architectural work remain open and are not treated as regressions against this baseline.

The historical Run #53 collection failure exposed a source-tree import collision involving the generic top-level package name `telegram`; the current test bootstrap explicitly prioritizes tgdrive's `app/telegram` package. Proxy Runtime and its optional SOCKS5 dependency were subsequently validated by CI, and the real deployment also validated SOCKS5 TCP/TLS plus Telethon authorization.

## Download speed optimization status

**Not complete.** The first benchmark is complete and is now the baseline for Phase 2. The next work is controlled transport profiling followed by bounded parallel chunk retrieval/reassembly and, if justified by measurements, shared caching. The goal is to remove unnecessary tgdrive bottlenecks; it is not to claim that Telegram service-side limits can be bypassed.

## Deployment portability requirements

TGDrive **must not bind deployment to Python 3.12**.

The supported deployment model is:

1. Detect the Python version actually available on the target server.
2. Check that the detected version satisfies TGDrive's declared compatibility range.
3. Create an isolated virtual environment using that server's compatible Python interpreter.
4. Install dependencies compatible with that interpreter.
5. Fail early with a clear compatibility error when the server's Python version is unsupported.
6. Do not replace or modify the operating system's default Python merely to satisfy TGDrive.

CI may use a newer Python version than a production server. CI's interpreter version is a test environment choice; it must not become an implicit production deployment requirement.

## Architectural rules going forward

1. Core business domains do not import concrete proxy or media implementations.
2. Download transport is a Core capability shared by all file types; it is not a Media Plugin.
3. Video remains frozen until the final Media Plugin phase unless benchmark evidence shows an abstraction is required earlier.
4. Proxy implementations remain optional infrastructure plugins.
5. Whether a deployment uses a proxy is determined by deployment configuration and server/network requirements, not by country or region checks in application code.
6. Before changing concurrency, establish repeatable benchmarks for direct and proxied Telegram paths where the deployment environment permits both.
7. Do not claim that Telegram-side limits can be bypassed; optimize the system so tgdrive, proxy, CPU and single-connection design are not unnecessary bottlenecks.

## Real-server deployment status

The Debian 12 real-server deployment is running successfully. PostgreSQL is healthy, the Core service is up, Telegram authorization succeeds, the configured source is scanned, and the file HTTP path has been verified. The deployment remains in the performance-optimization stage rather than being declared production-grade.
