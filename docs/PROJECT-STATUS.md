# Project Status

Updated 2026-09-01 after repository review and real-server validation. The target architecture in `docs/ARCHITECTURE.md` remains unchanged. This document records the current implementation, verified real-device behavior, deployment state, and the next optimization phase.

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
| Metadata-only discovery | `app/telegram/scanner.py`, `app/ingestion/*` | Aligned. Dialog discovery and ordinary scanning do not download complete payloads merely to enumerate metadata. |
| Logical Resource | `resources`, `files.resource_id`, `app/repositories/resources.py` | Aligned. Resource is the public logical entity; `files` is the physical Telegram backing-location store. |
| Physical Telegram identity | `account_id + telegram_chat_id + message_id` | Aligned. `topic_id` is retained as additional Telegram metadata. |
| Catalog/search | `app/catalog/*` | Aligned and real-device verified. Search and category filtering work. |
| Classification | `resource_categories`, `app/admin/api.py`, Resource-first Web UI | Aligned at Resource level. Single-resource classification works; batch classification remains planned. |
| Delivery | `app/delivery/*` | Aligned. Resource-first download/stream and HTTP Range are implemented. Real-device download works but throughput is the current P1 performance problem. |
| Source selection/failover | `app/delivery/source_selector.py` | Basic pre-transfer failover is implemented. Health scoring/ranking remains measurement-driven work. |
| Content verification | `app/ingestion/verification.py`, `ResourceRepository.verify_file()` | Implemented for complete non-range delivery; large real-device canonical-promotion validation remains pending. |
| Telegram account lifecycle | `app/core/lifecycle.py`, `app/telegram/api.py` | Implemented for enable/disable, reconnect and runtime reconciliation. Richer health/retirement administration remains planned. |
| Proxy boundary | `plugins/proxy/`, `app/plugins/runtime.py` | Aligned. Optional deployment-controlled plugin; reconnect rebuilds Telegram clients. Throughput comparison remains pending. |
| Admin Web UI | `app/web/index.html` | Telegram management sidebar with separate Dialogs and Source pages is implemented. |
| Web UI | `app/web/index.html` | Resource-first UI with login, catalog, search, filtering, classification, sharing and download is implemented. |
| Deployment | `docker-compose.yml`, `Dockerfile`, `.env.example`, `deploy.sh` | One-command fresh-host bootstrap is implemented; fixed proxy dependency is repository-contained. |

## Verified real-device flow

The core deployment-to-resource flow has been verified on the real test server:

```text
Fresh server
  → ./deploy.sh
  → optional proxy enablement
  → Telegram account login
  → automatic Dialog discovery
  → administrator selects/enables a resource dialog
  → Source enabled
  → Scanner starts immediately
  → Resource catalog populated
  → search/category/share/download
```

### Telegram accounts and sessions

- `default.session`: verified and reused successfully.
- `Asada.session`: verified with a distinct account name.
- Multiple Telegram account rows/sessions are supported.
- The login helper temporarily stops Core to avoid SQLite session locking, performs interactive authorization, then restarts Core.
- Running Core automatically reconciles enabled accounts and refreshes dialog metadata after authorization.

### Dialog discovery and Source lifecycle

- Dialog discovery is automatic after account authorization/reconciliation; no manual API command is required to refresh dialogs.
- Only selectable Telegram resource groups/channels are persisted for the administrator Dialog view.
- Non-resource private users/bots are filtered from the management selection surface.
- Dialogs and Sources are displayed as separate sidebar pages.
- Dialog actions are **Enable / Disable / Delete**.
- Enable creates or re-enables the corresponding Source and immediately makes it eligible for scanning.
- Disable stops that Source from being scanned and removes resources that no longer have an enabled Telegram source from the active catalog view.
- Delete removes the corresponding management Source/Dialog record and stops further scanning.
- Periodic Telegram reconciliation is one hour; administrator-triggered immediate reconciliation is available so removal does not require waiting for the scheduled cycle.
- Removed Telegram chats are reconciled so stale Dialog/Source state and their active catalog visibility are not retained indefinitely.

### Scanner

- Scanner is Source-scoped.
- With no enabled Sources, the scanner remains idle rather than repeatedly scanning all dialogs.
- Enabling a Source triggers immediate scanner processing.
- Incremental scanning uses persisted message state and later scans only newer messages.
- Ordinary scanning remains metadata-oriented; full payload downloads are not used merely to discover Resources.

### Catalog and classification

Verified:

- Administrator login: **PASS**
- Category creation: **PASS**
- Category deletion: **PASS**
- Category filtering: **PASS**
- Filename/resource search: **PASS**
- Resource catalog display: **PASS**

Known gap:

- Resource classification is currently one Resource at a time. Batch category assignment/removal is planned in Issue #30.
- Telegram Topic → Category automation is planned in Issue #29; `files.topic_id` is already available as the persistence hook.

### Sharing

Verified:

- Share link generation: **PASS**
- Share link display: **PASS**
- Share link deletion: **PASS**
- Shared link access: **PASS**
- Shared resource download: **PASS**

### Download

- Basic Resource download is **functionally working**.
- A ~276 MB MP4 (`files.id=9`, `resource_id=12`, `message_id=9`) is available for repeatable benchmarking.
- Real-device observation has shown roughly the 100 KB/s range, with a roughly 260 MB transfer taking about 10 minutes.
- The root cause has not yet been isolated, so speculative concurrency/request-size changes have intentionally not been merged.
- The next phase is a controlled benchmark separating Telegram → VPS, FastAPI → local client, public HTTP → client, and proxy/direct effects.

## Deployment status

### Fresh server

`deploy.sh` provides the one-command bootstrap path:

1. verify Docker and Compose;
2. create persistent directories;
3. collect required credentials when `.env` is absent;
4. generate deployment secrets;
5. write a protected `.env`;
6. validate `docker compose config`;
7. build Core;
8. initialize/start PostgreSQL + Core;
9. print service status.

The optional proxy is separately administrator-controlled and uses the fixed sing-box artifact committed to the repository, so proxy image creation does not require downloading sing-box from the Internet.

Telegram login and Source selection remain explicit post-bootstrap operations because they require account authorization and administrator intent.

### CI/deployment gate

GitHub Actions validates the Python test matrix, PostgreSQL integration, deployment/Compose validation, Core image build, and proxy image build. Recent repository work concentrated on Telegram dialog/source administration; the download optimization phase is intentionally separate from that control-plane work.

## Current work queue

### P1 — Download performance and resilience

**Issue #21 — Benchmark and optimize Resource download transport** is the immediate engineering priority.

The optimization must preserve these invariants:

- Resource-first delivery API.
- Physical Telegram identity `(account_id, telegram_chat_id, message_id)`.
- HTTP Range correctness.
- Pre-transfer source failover.
- No claim of bypassing Telegram service-side limits.

The benchmark should first establish where time is spent before introducing concurrency, request sizing, caching, or source ranking.

### Candidate download optimization directions

1. **Baseline/transport diagnosis** — measure direct Telegram throughput, FastAPI loopback, public HTTP, Range offsets, CPU/memory/network and proxy/direct paths. Lowest risk and mandatory first step.
2. **Single-account transport tuning** — optimize Telethon transfer/request behavior, buffering and bounded connection use after the benchmark identifies the bottleneck. Low-to-medium risk.
3. **Multi-account parallel range retrieval** — use multiple authorized Telegram accounts as independent access paths to fetch different byte ranges concurrently, then reassemble them behind the existing Resource delivery contract. Potentially high benefit when the bottleneck is per-connection/account transfer, but requires careful bounded concurrency, ordering, retry and Range validation.
4. **Multi-account source failover/ranking** — measure per-account/source health and prefer healthier/faster Telegram-backed locations while retaining pre-transfer failover. This improves resilience and can improve effective throughput, but should follow measurement rather than assumptions.
5. **Bounded cache / hot-resource acceleration** — cache only after measuring whether repeated downloads are a meaningful workload and after defining disk/memory limits and invalidation. This can improve repeat-download latency but does not solve first-download Telegram throughput.

Multiple Telegram accounts and API credentials are therefore potentially useful for **download optimization**, but not automatically faster. They become valuable if the same logical Resource has multiple Telegram-backed locations or if Telegram transfer limits are materially per-account/per-connection. The benchmark must verify this on the real deployment before introducing parallel multi-account downloading.

### P2 — Source resilience

Issue #19 tracks richer Resource-level source health, retry policy and ranking. It should consume measurements from Issue #21 rather than independently inventing a scheduling policy.

### P2 — Admin/product improvements

- Issue #29: Telegram supergroup Topic → Category mapping.
- Issue #30: batch Resource category operations.
- Issue #18: richer Telegram account health/retirement administration.
- Issue #15: further Scanner/Ingestion orchestration refinement.
- Issue #22: internal `telegram` package namespace cleanup.

## Target architecture preservation

The current project progress and planned download optimization do **not** change the target architecture. These remain invariants:

- Telegram is the only content backend.
- Resource is the public logical content entity.
- Telegram message is the physical source record.
- `files` remains a physical Telegram backing-location persistence table, not a public File API.
- Categories attach to Resources.
- Telegram accounts are access/redundancy paths, not storage-provider backends.
- Proxy is deployment-controlled infrastructure.
- Ordinary scanning is metadata-only.
- Admin APIs/UI are a control plane and must not become a mandatory hop in the download data path.
- Video/chunk caching remains outside Core unless separately designed and validated.

## Exit criteria for the next milestone

The next milestone is **download performance/resilience validation**. It is complete when:

1. the dominant download bottleneck is identified with a repeatable benchmark;
2. an optimization improves measured throughput without breaking Range/failover behavior;
3. multiple-account usefulness is measured rather than assumed;
4. direct/proxy behavior is characterized;
5. complete large-file verification/canonical promotion is validated;
6. browser download/stream regression tests pass;
7. only then are further performance mechanisms such as multi-account parallel retrieval or caching selected.
