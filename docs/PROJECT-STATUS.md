# Project Status

Updated 2026-08-31 after repository/code review and real-server validation. The target architecture in `docs/ARCHITECTURE.md` remains unchanged. This document records the current implementation, verified real-device behavior, deployment state, and work that remains.

## Product definition

tgdrive is a **Telegram-only** file catalog and delivery system.

```text
Telegram metadata
      ↓
Recognition / Ingestion
      ↓
Logical Resource
      ↓
Catalog + classification + search
      ↓
Download / Range delivery
      ↓
Telegram backing locations
```

No generic storage-provider abstraction is required or planned. Telegram accounts are access/redundancy paths, not storage providers.

## Architecture-to-code review

| Target responsibility | Current implementation | Assessment |
|---|---|---|
| Telegram accounts/sessions | `app/telegram/client.py`, `app/telegram/login.py`, `app/repositories/accounts.py` | Aligned. Account-named sessions under `/data/accounts/<name>` are working on the real server. |
| Telegram source configuration | `app/telegram/api.py`, `app/repositories/sources.py` | Aligned. Sources are explicitly configured by account + Telegram chat ID. |
| Metadata-only discovery | `app/telegram/scanner.py`, `app/ingestion/*` | Aligned. Scanner indexes message metadata and does not download complete payloads during indexing. |
| Logical Resource | `resources`, `files.resource_id`, `app/repositories/resources.py` | Aligned. Resource is the public logical entity; `files` is the physical Telegram backing-location store. |
| Physical Telegram identity | `account_id + telegram_chat_id + message_id` | Aligned and verified against the real database. `topic_id` is already present in `files` but is not yet used for automatic classification. |
| Catalog/search | `app/catalog/*` | Aligned and real-device verified. Search and category filtering work. |
| Classification | `resource_categories`, `app/admin/api.py`, Resource-first Web UI | Aligned at Resource level. Single-resource assignment and category deletion are real-device verified. Batch classification is not yet implemented. |
| Delivery | `app/delivery/*` | Aligned. Resource-first download/stream and HTTP Range are implemented. Real-device download is functional but currently too slow. |
| Source selection/failover | `app/delivery/source_selector.py` | Aligned at the basic pre-transfer failover boundary. Health scoring/ranking remains deferred until measurements. |
| Content verification | `app/ingestion/verification.py`, `ResourceRepository.verify_file()` | Implemented in the current code path for complete non-range delivery; real-device canonical-promotion behavior still needs explicit validation. |
| Telegram account lifecycle | `app/core/lifecycle.py`, `app/telegram/api.py` | Partially complete. Enable/disable, reconnect and runtime scanner reconciliation exist. A richer admin health/retirement surface remains. |
| Proxy boundary | `plugins/proxy/`, `app/plugins/runtime.py` | Aligned. Optional deployment-controlled plugin; reconnect endpoint rebuilds Telegram clients. Real proxy throughput/smoke validation remains pending. |
| Web UI | `app/web/index.html` | Aligned Resource-first UI. Login, catalog, search, filtering, classification, sharing and download are present. |
| Deployment | `docker-compose.yml`, `Dockerfile`, `.env.example`, `deploy.sh` | Now has a one-command fresh-host bootstrap path; CI validates Compose parsing, deployment scripts and Core image build. |

## Real-device validation — completed

The current real server is `~/tgdrive-test/tgdrive` and is running the same `main` code baseline as the repository.

### Telegram accounts and sessions

- `default.session`: verified and reused successfully.
- A custom account name was also verified with `Asada.session`.
- The login helper creates the requested account-named session; the earlier `default.session` observation was an operation/test invocation issue, not a code defect.
- PostgreSQL contains enabled account rows for `default` and `Asada`.
- Both accounts reconnect and authorize successfully in the running service.

### Telegram source and scanning

- Source configured: `My Documents`, chat ID `-1004413553797`, account `default`.
- Dialog discovery through the authenticated admin API works.
- Scanner found the configured dialog and indexed Telegram resources.
- Incremental scanning is working: `last_message_id` advanced and later scans only process newer messages.
- Existing indexed files are not counted as new files on every incremental pass; this is expected behavior.
- A later incremental scan detected one newly added file, confirming the incremental path.

### Catalog and classification

Verified from the browser:

- Administrator login: **PASS**
- Category creation: **PASS**
- Category deletion: **PASS**
- Category filtering: **PASS**
- Filename/resource search: **PASS**
- Resource catalog display: **PASS**

Current limitation: classification is still one Resource at a time. Batch selection and batch category assignment are planned.

### Sharing

Verified from the browser:

- Share link generation: **PASS**
- Share link displayed under the Resource: **PASS**
- Share link deletion by administrator: **PASS**
- Shared link access: **PASS**
- Shared resource download: **PASS**
- Browser clipboard behavior was initially unreliable, but the visible concrete-link workflow is now confirmed usable.

### Download

- Resource download is functionally working.
- A ~276 MB MP4 (`files.id=9`, `resource_id=12`, `message_id=9`) is available for repeatable benchmark testing.
- Real-device observation: download throughput is currently only around the 100 KB/s range and is significantly slower than acceptable; a roughly 260 MB transfer was observed taking about 10 minutes.
- Root cause has **not** yet been isolated. No speculative transport optimization has been applied yet.
- The next step is a controlled Telegram → VPS → FastAPI → browser benchmark matrix.

### Telegram connectivity anomaly during testing

A standalone ad-hoc Telethon diagnostic attempted to connect the `default` session and repeatedly timed out. This did not indicate a service outage because the production application subsequently connected and authorized both `default` and `Asada` successfully and continued scanning. The timeout is therefore treated as a diagnostic/network-path anomaly until the benchmark distinguishes direct/proxy/connection behavior.

### Topic support

- `files.topic_id` already exists in the persistence model.
- Automatic Telegram supergroup Topic recognition and Topic → Category mapping are **not implemented yet**.
- This is a planned extension of the existing Telegram metadata/Resource model, not a change to the target architecture.

## Real-device validation — pending

1. Download chain benchmark: Telegram → VPS, FastAPI → local VPS, browser → VPS.
2. Direct versus proxy throughput comparison where applicable.
3. Download behavior at multiple byte ranges/offsets and repeated requests.
4. Multi-account Resource failover under a controlled source failure.
5. HTTP Range correctness on a large real file.
6. Complete-download SHA-256 verification and canonical Resource promotion.
7. Optional proxy connectivity/reconnect smoke test.
8. Large-file behavior for resources above 2 GiB/4 GiB where Telegram/account limits apply.
9. Telegram supergroup Topic recognition and automatic Topic → Category mapping after implementation.
10. Batch Resource classification after implementation.

## Known functional/engineering gaps

### P1/P2 work that should remain measurement-driven

- Download transport optimization: Issue #21. Current performance is poor enough to prioritize benchmark-driven investigation.
- Resource source health/ranking and richer retry policy: Issue #19.
- Telegram account admin health/retirement lifecycle: Issue #18.
- Further Scanner/Ingestion orchestration refinement: Issue #15.
- Internal top-level `telegram` package namespace cleanup: Issue #22.

### Planned product improvements

- Telegram Topic metadata normalization and Topic → Category mapping.
- Batch Resource category assignment/removal from the admin UI and a transactional batch API.
- Per-source scheduling alignment with persisted `telegram_sources.scan_interval` if deployment requirements justify it.

## Deployment status

### Fresh server

A new `deploy.sh` bootstrap is now part of `main`.

It:

1. verifies Docker and the Compose plugin;
2. creates persistent `data/accounts` and `data/postgres` directories;
3. interactively collects Telegram API credentials, phone and Web admin password when `.env` does not exist;
4. generates deployment secrets with `openssl`;
5. writes a protected `.env`;
6. validates `docker compose config`;
7. builds and starts PostgreSQL + Core;
8. prints the resulting service status.

The command is:

```bash
./deploy.sh
```

An existing `.env` is preserved. Environment variables can be supplied for non-interactive bootstrap. Telegram login and Telegram source selection intentionally remain explicit post-bootstrap operations because they require account authorization and an operator-selected chat.

### CI deployment gate

GitHub Actions now additionally validates:

- shell syntax for `deploy.sh` and `login-account.sh`;
- Compose configuration parsing;
- Core Docker image build;
- Proxy plugin Docker image build;
- the existing full PostgreSQL test suite on Python 3.11 and 3.12.

## Target architecture preservation

The deployment and documentation work above does **not** change the target architecture. In particular, the following remain architectural invariants:

- Telegram is the only content backend.
- Resource is the public logical content entity.
- Telegram message is the physical source record.
- `files` remains a physical Telegram backing-location persistence table, not a public File API.
- Categories attach to Resources.
- Telegram accounts are access/redundancy paths.
- Proxy is deployment-controlled infrastructure.
- Ordinary scanning remains metadata-only.
- Video/chunk caching remains outside Core.

## Real-device exit criteria

The project is no longer in a generic "ready for first real-device test" state. The first real-device phase has been completed successfully for login, source configuration, scanning, catalog/search/classification, sharing and basic delivery. The remaining gate is **delivery performance + resilience validation**, followed by Topic automation and batch classification work.
