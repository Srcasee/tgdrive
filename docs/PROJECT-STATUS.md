# Project Status

Updated 2026-09-03 after repository review and code-level investigation. The target architecture in `docs/ARCHITECTURE.md` remains unchanged. This document records the current implementation status, verified behavior, known issues, and current engineering priorities.

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

Telegram accounts are access/redundancy paths, not storage providers.

## Architecture-to-code review

| Target responsibility | Current implementation | Assessment |
|---|---|---|
| Telegram accounts/sessions | `app/telegram/*`, account repositories | Implemented |
| Telegram source configuration | `app/telegram/api.py`, `app/repositories/sources.py` | Implemented |
| Metadata-only discovery | `app/telegram/scanner.py`, ingestion modules | Implemented |
| Logical Resource | Resource repositories and catalog layer | Implemented |
| Physical Telegram identity | `account_id + telegram_chat_id + message_id` | Implemented. `files.topic_id` represents Telegram `message_thread_id` semantics and is additional Telegram message metadata, not part of Resource identity. |
| Catalog/search | Catalog layer and Web UI | Implemented |
| Classification | Resource-category mapping | Implemented. Batch operations remain planned. |
| Delivery | Delivery layer | Implemented. Current priority is state consistency investigation, not throughput optimization. |
| Source selection/failover | Source selector | Basic pre-transfer failover implemented. |
| Admin Web UI | Telegram Dialog and Source management UI | Implemented. Runtime lifecycle issues are under investigation. |

## Verified flow

```text
Fresh server
  → deploy
  → Telegram account login
  → Dialog discovery
  → administrator enables Source
  → Scanner processes metadata
  → Resource catalog populated
  → search/category/share/download
```

## Telegram Topic metadata

The database field `files.topic_id` is kept for Telegram topic context.

Current interpretation:

```text
Telegram API concept:
message_thread_id

Internal database field:
topic_id
```

This metadata may support future Telegram Topic → Category automation, but it does not participate in Resource identity or deduplication.

## Scanner and Source lifecycle

Current architecture remains account-level scanner orchestration.

Important behavior:

- Scanner reads enabled Sources from persistence.
- Normal scanning remains metadata-oriented.
- Full payload download is not used only for discovery.

Known issue:

After a fresh deployment, enabling one Telegram group may immediately populate resources while subsequently enabled groups may not appear until another lifecycle event occurs.

Investigation result:

- Source state persistence works.
- Scanner discovery logic reloads enabled Sources.
- The remaining issue is runtime synchronization: Source lifecycle changes do not reliably interrupt the active scanner cycle.

Planned fix:

- Keep the account-level scanner model.
- Add scanner wakeup behavior when Source configuration changes.
- Avoid unnecessary coupling between Source changes and Dialog reconciliation.

## Admin management known issues

### Source toggle triggers unnecessary Dialog refresh

Current behavior:

```text
Enable/Disable Source
        ↓
Runtime reconciliation
        ↓
Dialog refresh
```

Problem:

Source lifecycle management and Telegram Dialog discovery have different responsibilities. Source enable/disable should update scanning state without forcing Dialog discovery.

### Source enable synchronization

Known symptom:

```text
Fresh deployment
A enabled → resources appear
B/C enabled → resources may not appear
```

Root cause investigation:

The problem is related to scanner runtime wakeup and lifecycle synchronization rather than database Source creation.

## Download status

Basic Resource download is functionally implemented.

The previous assumption that throughput optimization was the immediate P1 item is outdated.

Current known issues:

- Some downloads restart after partial progress.
- Some resources that appear completed may later fail with file extraction errors.
- The exact state consistency failure has not yet been isolated.

Current priority:

```text
Download state consistency investigation
```

Performance optimization, concurrency tuning, and transport changes are intentionally postponed until download state handling is reliable.

## Current work queue

### P1 — Runtime and download consistency

1. Fix Source lifecycle → scanner wakeup synchronization.
2. Remove unnecessary Dialog refresh coupling from Source operations.
3. Investigate download resume/completion/file extraction state handling.

### P2 — Product improvements

- Telegram Topic → Category mapping.
- Batch Resource category operations.
- Richer Telegram account health administration.
- Scanner/Ingestion orchestration refinement.

## Target architecture preservation

The architecture remains unchanged:

- Telegram is the only content backend.
- Resource is the public logical entity.
- Telegram messages are physical source records.
- `files` stores Telegram backing locations.
- Categories attach to Resources.
- Telegram accounts are access/redundancy paths.
- Proxy is deployment-controlled infrastructure.
- Scanner remains metadata-oriented.
- Admin APIs/UI are control-plane components and must not become part of the download data path.

## Next milestone exit criteria

The next milestone is complete when:

1. Source lifecycle changes immediately affect scanner behavior.
2. Dialog discovery and Source management are correctly separated.
3. Download completion/resume state is reliable.
4. Performance optimization can proceed based on validated behavior.
