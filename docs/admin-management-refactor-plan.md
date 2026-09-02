# Admin Management Interface Refactor Plan

This document defines the future admin panel architecture. The existing tgdrive deployment architecture remains unchanged.

Core architecture:

- Telegram runtime handles login and reconciliation.
- Scanner indexes enabled Telegram sources.
- Database Resource/File model remains unchanged.
- Admin panel operates through APIs.

## Sidebar

Dashboard

Telegram:
- Dialogs
- Sources
- Recycle Bin

Resources:
- Resource List
- Categories
- Batch Operations

Downloads
System
Settings

## Dialogs

Only show Telegram resource containers:

- supergroups
- channels

Exclude:

- users
- bots
- private chats

Each dialog uses one status switch.

Enabled:

- create Source
- enable scanner
- immediately trigger scan
- display resources in Sources page

Disabled:

- disable scanner
- stop indexing
- hide related source resources

Delete:

- stop scanning
- remove dialog configuration
- remove source relationship
- move related data to recycle bin
- trigger reconciliation refresh

## Sources

Separate page displaying enabled sources only.

Functions:

- resource browsing
- scan status
- manual scan
- category assignment
- batch category operations

## Recycle Bin

All frontend deletions enter recycle bin.

Supports:

- restore
- permanent deletion

This prevents deleted Telegram resources returning after reconciliation.

## Scanner Flow

Telegram Login -> Dialog Reconciliation -> Enable Dialog -> Create Source -> Immediate Scanner Start -> Resource Index

## Future

Topic automatic classification:

- detect forum topics
- analyze topic title
- assign categories automatically

## Implementation Order

1. Stabilize download pipeline.
2. Keep deployment architecture unchanged.
3. Refactor admin APIs.
4. Implement sidebar frontend.
5. Separate Dialogs and Sources.
6. Add recycle bin.
7. Add batch operations.
8. Add topic classification.
