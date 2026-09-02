# Admin Management Interface Refactor Plan

## Goal

Refactor the management panel without changing tgdrive core architecture.

- Telegram runtime handles authentication and reconciliation.
- Scanner indexes enabled Telegram sources.
- Resource/File database model remains unchanged.
- Admin panel manages configuration through APIs.

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

Only display Telegram resource containers:

- supergroups
- channels

Exclude users, bots and private chats.

Each dialog has one status switch.

Enabled creates a Source, enables scanner and triggers immediate scanning.

Disabled stops scanner and hides related active source data.

Delete stops scanning, removes configuration, moves data to recycle bin and triggers reconciliation refresh.

## Sources

Separate page showing enabled sources only.

Functions:

- resource browsing
- scan status
- manual scan
- category assignment
- batch operations

## Recycle Bin

All frontend deleted content enters recycle bin.

Supports restore and permanent deletion.

## Scanner Flow

Telegram Login -> Dialog Reconciliation -> Enable Dialog -> Create Source -> Immediate Scanner Start -> Resource Index

## Future

Topic automatic classification based on Telegram forum topics and metadata.

## Order

1. Stabilize download pipeline.
2. Keep deployment architecture unchanged.
3. Refactor admin APIs.
4. Implement sidebar.
5. Separate Dialogs/Sources.
6. Add recycle bin.
7. Add batch operations.
8. Add topic classification.
