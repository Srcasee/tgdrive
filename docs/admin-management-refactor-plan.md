# Admin Management Interface Refactor Plan

## Goal

Refactor management panel without changing tgdrive core architecture.

## Structure

Sidebar:

- Dashboard
- Telegram
  - Dialogs
  - Sources
  - Recycle Bin
- Resources
- Downloads
- System
- Settings

## Dialogs

Only show Telegram supergroups and channels. Exclude users, bots and private chats.

Each dialog uses one status switch:

Enabled:
- create Source
- enable scanner
- trigger immediate scan

Disabled:
- stop scanner
- hide active source resources

Delete:
- stop scanning
- remove configuration
- move data to recycle bin
- refresh reconciliation

## Sources

Separate page for enabled sources.

Supports:
- resource browsing
- scan status
- manual scan
- categories
- batch operations

## Recycle Bin

Deleted frontend data enters recycle bin and can be restored or permanently deleted.

## Scanner Flow

Telegram Login -> Dialog Reconciliation -> Enable Dialog -> Source -> Scanner -> Resources

## Future

Topic-based automatic classification.

## Order

1. Stabilize download pipeline.
2. Keep architecture unchanged.
3. Refactor APIs.
4. Build sidebar management.
5. Add recycle bin.
6. Add batch operations.
