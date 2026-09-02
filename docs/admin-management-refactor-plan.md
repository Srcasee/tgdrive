# Admin Management Interface Refactor Plan

## Goal

Refactor the management panel without changing tgdrive core architecture.

Core modules remain:

- Telegram runtime: authentication and dialog reconciliation
- Scanner: indexing enabled Telegram sources
- Database: existing Resource/File model
- Download pipeline: independent module

The admin panel only manages configuration and operations through APIs.

## Sidebar Layout

```
Dashboard
Telegram
 ├─ Dialogs
 ├─ Sources
 └─ Recycle Bin
Resources
 ├─ Resource List
 ├─ Categories
 └─ Batch Operations
Downloads
System
Settings
```

## Dialogs

Dialogs page only shows resource containers:

- Telegram supergroups
- Telegram channels

Exclude users, bots and private chats.

Each dialog has one status switch.

Enabled:
- create telegram_source
- enable scanner
- trigger immediate scan
- show resources in Sources

Disabled:
- disable scanner
- stop indexing
- hide related source resources

Delete:
- stop scanning
- remove dialog configuration
- remove source relationship
- move data to recycle bin
- trigger reconciliation refresh

## Sources

Independent page showing enabled sources only.

Functions:

- resource browsing
- scan status
- manual scan
- category assignment
- batch category operations

## Recycle Bin

First-level menu.

All frontend deleted objects enter recycle bin.

Supports restore and permanent deletion.

## Scanner Flow

Telegram Login -> Dialog Reconciliation -> Enable Dialog -> Create Source -> Immediate Scanner Start -> Resource Index

Disabled or deleted dialogs must never be scanned.

## Future

Topic based automatic classification:

- detect forum topics
- analyze topic title
- assign categories automatically

## Implementation Order

1. Stabilize download pipeline.
2. Keep deployment architecture unchanged.
3. Refactor admin APIs.
4. Implement sidebar navigation.
5. Separate Dialogs and Sources.
6. Add recycle bin.
7. Add batch operations.
8. Add topic classification.
