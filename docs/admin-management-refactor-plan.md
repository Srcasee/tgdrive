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

Implementation order:
1. Download stability
2. Preserve architecture
3. Admin APIs
4. Sidebar UI
5. Dialog/Source separation
6. Recycle bin
7. Batch operations
8. Topic classification
