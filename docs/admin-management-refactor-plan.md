# Admin Management Interface Refactor Plan

The management refactor keeps tgdrive core architecture unchanged.

Modules:
- Telegram runtime: authentication and reconciliation
- Scanner: enabled source indexing
- Database: existing Resource/File model
- Download pipeline: independent

Admin sidebar:
- Dashboard
- Telegram
  - Dialogs
  - Sources
  - Recycle Bin
- Resources
- Downloads
- System
- Settings

Dialogs:
- only show resource groups/channels
- exclude users, bots, private chats
- one status toggle

Enable:
- create source
- enable scanner
- immediate scan

Disable:
- stop scanner
- hide source resources

Delete:
- stop scanner
- remove configuration
- move data to recycle bin
- refresh reconciliation

Sources page:
- enabled sources only
- resource browsing
- scan status
- manual scan
- category management
- batch operations

Recycle Bin:
- deleted content goes here first
- restore
- permanent delete

Future:
- topic automatic classification

## Known issues during refactor validation

### Source toggle refresh coupling

Enable/disable actions must not trigger Dialog discovery refresh.

Current issue:

- Source state changes refresh part of the DOM.
- The refresh path can trigger Dialog fetching.
- Dialog discovery and Source lifecycle are separate concerns and should remain decoupled.

Expected behavior:

- Enable/disable refreshes Source state only.
- Dialog discovery is triggered only by reconciliation or explicit Dialog operations.

### Source runtime synchronization after fresh deployment

Observed behavior:

- After a fresh deployment, enabling Source A can populate resources correctly.
- Enabling additional Sources B/C may not immediately populate resources.
- After individually toggling Sources, later combinations behave normally.

Suspected area:

- Database Source enabled state and in-memory scanner runtime state may become temporarily inconsistent.
- Validation should trace Source enable API, runtime notification, scanner reconciliation and scanner task creation.

## Implementation order

1. Download stability
2. Preserve architecture
3. Admin APIs
4. Sidebar UI
5. Dialog/Source separation
6. Recycle bin
7. Batch operations
8. Topic classification
