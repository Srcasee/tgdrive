# Admin Management Interface Refactor Plan v2

## Goal

Transform TGDrive Admin from a mixed management page into a domain-separated control plane while preserving the current backend architecture:

- `app/core` remains lifecycle orchestration only.
- `app/telegram` keeps Telegram discovery, scanner and downloader domains.
- Admin only controls configuration and displays runtime state through APIs.

Core domain boundaries:

```text
Dialog Discovery
        |
        v
Dialogs cache

Admin Dialog management
        |
        v
Source configuration
        |
        v
Scanner runtime
        |
        v
Catalog / Ingestion / Resources
```

---

# 1. New Sidebar Structure

```text
TGDrive Admin

├── Dashboard
│
├── Telegram
│    ├── Accounts
│    ├── Dialogs
│    └── Sessions
│
├── Resources
│    ├── Sources
│    ├── Files
│    └── Categories
│
├── Scanner
│    ├── Tasks
│    ├── Logs
│    └── Settings
│
├── Download
│    ├── Active
│    └── History
│
├── System
│    ├── Config
│    └── API
│
└── Recycle Bin
```

---

# 2. Dialog Domain

Dialog represents Telegram discovery results.

Responsibilities:

- store Telegram channel/group discovery data
- display available Telegram sources
- provide explicit reconciliation entry

Dialog does not own:

- scanner state
- download state
- resource lifecycle

Important rules:

- Opening Dialog page reads cached dialog data.
- First initialization may perform lazy discovery when cache is empty.
- Refreshing browser pages must not repeatedly trigger discovery.
- Manual reconciliation remains explicit.

Recommended model:

```text
Dialog
  |
  +-- discovered Telegram metadata
```

---

# 3. Source Domain

Source represents user-selected scanning configuration.

Responsibilities:

- enable/disable scanning
- manage scan status
- trigger scanner actions
- maintain source metadata

Flow:

```text
Enable Source
      |
      v
Create/update Source
      |
      v
ScannerManager wakeup
      |
      v
Scanner
```

Important:

Dialog must not contain scanner configuration state.

Source disable:

```text
Source.enabled=false
        |
        v
Stop scanning this source
        |
        v
Keep existing resources
```

Resources are hidden by policy, not deleted.

---

# 4. Delete and Recycle Bin Design

Delete is not physical removal for discovered Telegram objects.

Flow:

```text
Delete Dialog
      |
      v
Recycle Bin / Ignore state
      |
      v
Discovery will not restore automatically
```

Future unified recycle model:

```text
recycle_items

id
object_type
object_id
deleted_at
```

Supported objects:

- Dialog
- Source
- Resource
- Download task

---

# 5. Resource and Category System

Categories become independent entities:

```text
categories

id
name
parent_id
```

Example:

```text
Movies
 ├── Domestic
 ├── Europe
 └── Asia

TV
 ├── US
 └── Korea
```

Resource classification should support multiple categories:

```text
resource_categories

resource_id
category_id
```

---

# 6. Topic Automatic Classification

Telegram topic mapping should use Telegram API terminology:

```text
message_thread_id
```

Future mapping:

```text
Telegram Topic
        |
        v
Scanner
        |
        v
message_thread_id
        |
        v
topic_category_mapping
        |
        v
Category
```

---

# 7. Scanner Management

Scanner becomes an observable runtime domain.

New views:

- Tasks
- Logs
- Settings

Possible runtime model:

```text
scanner_tasks

id
source_id
status
started_at
finished_at
error
```

Current behavior retained:

- Source changes wake Scanner.
- Scanner performs full enabled Source scan.
- Incremental scanning is deferred.

---

# 8. Download Management

Download UI separates:

```text
Active
History
```

Downloader and Delivery architecture remain unchanged.

---

# 9. Frontend State Isolation

Current known issue:

- Source enable/disable may trigger unnecessary dialog refresh requests.

Future rule:

```text
Dialogs page
    |
    +-- Dialog API

Sources page
    |
    +-- Source API

Scanner page
    |
    +-- Runtime API
```

No cross-domain implicit refresh.

---

# 10. API Refactor Direction

Current backend modules are domain modules, not necessarily URL prefixes.

Target organization:

```text
/dashboard
/telegram/accounts
/telegram/dialogs
/telegram/sessions
/resources/sources
/resources/files
/resources/categories
/scanner/tasks
/scanner/logs
/download
/system
/recycle
```

Migration should be incremental.

---

# 11. Implementation Order

1. Introduce Admin V2 frontend structure.
2. Separate Dialog and Source API responsibilities.
3. Migrate Dialog page.
4. Migrate Source page.
5. Add Scanner runtime pages.
6. Add Resource and Category management.
7. Add Download management.
8. Add Recycle Bin workflow.

---

# Deferred Issues

## Admin DOM refresh coupling

Known issue:

Source operations can cause unnecessary Dialog UI refresh.

Deferred to Admin V2.

## Source full scan optimization

Current behavior retained for correctness:

Source wakeup triggers full enabled Source scan.

Incremental scanning is future optimization.

## Download retry/resume bug

Independent from Admin refactor.
