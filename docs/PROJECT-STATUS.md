# Project Status and Target Alignment

Updated for real-server deployment preparation.

## Current implemented capabilities

### Core ingestion and indexing

- Telegram session discovery and account synchronization.
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

### Administration

- Category persistence.
- Category CRUD API/UI.
- File-to-category assignment.
- Telegram source validation and uniqueness.
- Telegram session credentials are kept server-side and are not returned by account APIs.

### Infrastructure extensibility

- Proxy plugin interface and Python entry-point discovery.
- Independent SOCKS5 proxy plugin.
- Proxy selection is deployment configuration, not geographic logic embedded in Core.

## Not yet implemented

- Production-grade runtime proxy hot-plug/reload.
- Account-scoped proxy selection and routing policy.
- High-speed Download Manager with parallel chunk scheduling/reassembly.
- Shared local/object cache for popular files.
- Image online viewer.
- Generic Media Plugin manager.
- Audio/media plugin implementations.

## Alignment with the original goal

The project is **aligned with the requested product direction**, but not all target capabilities are implemented yet.

| Original goal | Current state | Alignment |
|---|---|---|
| Files uploaded to private TG groups are scanned/indexed | Implemented | Yes |
| Users search files on Web | Implemented | Yes |
| Users download files | Implemented | Yes |
| Admin classifies files | Implemented | Yes |
| Deploy in different regions | Supported by configuration/proxy plugin boundary | Yes |
| Proxy is hot-pluggable | Plugin discovery exists; production runtime hot-plug still needs hardening | Partial |
| Video playback | Implemented as Core service and frozen | Yes, intentionally not yet a plugin |
| Image online browsing | Not implemented | Future |
| Other media features are extensible plugins | Generic media plugin boundary not implemented | Future |
| Download speed should not be unnecessarily limited by tgdrive | First transport safeguards implemented | Phase 2 required |

## Deployment portability requirements

TGDrive **must not bind deployment to Python 3.12**.

The supported deployment model is:

1. Detect the Python version actually available on the target server.
2. Check that the detected version satisfies TGDrive's declared minimum/maximum compatibility range.
3. Create an isolated virtual environment using that server's compatible Python interpreter.
4. Install dependencies compatible with that interpreter.
5. Fail early with a clear compatibility error when the server's Python version is unsupported.
6. Do not replace or modify the operating system's default Python merely to satisfy TGDrive.

CI may use a newer Python version than a production server. CI's interpreter version is a test environment choice; it must not become an implicit production deployment requirement.

This requirement is intentionally documented now. The deployment tooling that automates version detection and dependency compatibility checks is a later infrastructure task and is **not** part of the current real-server baseline exercise.

## Architectural rules going forward

1. Core business domains do not import concrete proxy or media implementations.
2. Download transport is a Core capability shared by all file types; it is not a Media Plugin.
3. Video remains frozen until the final Media Plugin phase unless benchmark evidence shows an abstraction is required earlier.
4. Proxy implementations remain optional infrastructure plugins.
5. Whether a deployment uses a proxy is determined by deployment configuration and server/network requirements, not by country or region checks in application code.
6. Before Phase 2 performance work, establish a real throughput benchmark for direct and proxied Telegram paths where the deployment environment permits both.
7. Do not claim that Telegram-side limits can be bypassed; optimize the system so tgdrive, proxy, CPU and single-connection design are not unnecessary bottlenecks.

## Phase 1 status

Phase 1 is functionally complete at the Core architecture level. The historical Run #53 collection failure exposed a source-tree import collision involving the generic top-level package name `telegram`; the current test bootstrap explicitly prioritizes tgdrive's `app/telegram` package. Proxy Runtime and its optional SOCKS5 dependency were subsequently validated by CI Run #70 with the full test suite passing.

## Real-server deployment status

The first target is a Debian 12 server currently running Python 3.11.2. The server is being used as a real deployment/performance environment, not as a requirement that all TGDrive deployments use Python 3.11. The deployment is intentionally staged so each infrastructure layer can be validated independently before the next layer is enabled.
