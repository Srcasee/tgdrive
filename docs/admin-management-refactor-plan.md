# Admin Management Interface Refactor Plan V4

## Goal

Rewrite the management frontend as an independent Admin application.

The existing management frontend is not migrated for compatibility. Old admin injection code and transitional structures are not part of the final architecture.

The Admin interface is only a control plane. Backend domain boundaries remain unchanged.

```text
Admin UI
   |
   +-- API Client
          |
          +-- Telegram
          +-- Resources
          +-- Scanner
          +-- Download
          +-- System
          +-- Recycle Bin
```

---

# 1. Target Admin Architecture

The final navigation structure:

```text
TGDrive Admin

Dashboard

Telegram
 ├ Accounts
 ├ Dialogs
 └ Sessions

Resources
 ├ Sources
 ├ Files
 └ Categories

Scanner
 ├ Tasks
 ├ Logs
 └ Settings

Download
 ├ Active
 └ History

System
 ├ Config
 └ API

Recycle Bin
```

Each menu item owns its own page state and data loading logic.

Rules:

- A page only refreshes its own data.
- Dialog operations never refresh Source data automatically.
- Source operations never trigger Dialog Discovery.
- Scanner status is independent from Telegram discovery.
- No global DOM coupling between modules.

---

# 2. Frontend Structure

Use native JavaScript modules. No frontend framework is introduced at this stage.

Target structure:

```text
app/web/

├── admin.html
│
└── admin/
    ├── app.js
    ├── api.js
    ├── router.js
    ├── layout.js
    │
    ├── dashboard.js
    ├── telegram.js
    ├── resources.js
    ├── scanner.js
    ├── download.js
    ├── system.js
    └── recycle.js
```

The structure intentionally avoids excessive directory nesting. Domain modules own their internal pages.

---

# 3. Module Responsibilities

## app.js

Responsible for:

- Admin authentication check
- Application startup
- Loading layout and router

## api.js

Responsible for:

- HTTP request wrapper
- Authentication handling
- Common API error handling

Pages must not directly implement duplicated fetch logic.

## router.js

Responsible for:

- Menu navigation
- Loading domain modules

---

# 4. Telegram Module

```text
Telegram
 ├ Accounts
 ├ Dialogs
 └ Sessions
```

Responsibilities:

Accounts:

- Telegram client account status

Dialogs:

- Display discovered Telegram channels
- Enable Source configuration
- Disable Source configuration
- Move disabled dialogs to recycle workflow

Sessions:

- Session management

Dialogs do not perform:

- Scanner execution
- Resource scanning
- Download management

Flow:

```text
Telegram Discovery
        |
        v
Dialogs
        |
        v
Enable Source
        |
        v
telegram_source
```

---

# 5. Resources Module

```text
Resources
 ├ Sources
 ├ Files
 └ Categories
```

Sources:

```text
Source enabled
      |
      v
telegram_source
      |
      v
ScannerManager
      |
      v
Scanner
```

Files:

- Resource browsing
- Metadata management

Categories:

- Category tree
- Resource classification

---

# 6. Scanner Module

```text
Scanner
 ├ Tasks
 ├ Logs
 └ Settings
```

Responsible only for scanner runtime visibility and configuration.

It does not perform Telegram Dialog Discovery.

---

# 7. Download Module

```text
Download
 ├ Active
 └ History
```

Responsible for:

- Current download tasks
- Historical download records

Downloader and Delivery backend architecture remain unchanged.

---

# 8. System Module

```text
System
 ├ Config
 └ API
```

Responsible for system administration information.

---

# 9. Recycle Bin

Recycle Bin is a first-class module.

Functions:

- View deleted objects
- Restore
- Permanent deletion

Deletion workflow:

```text
Disabled Dialog
        |
        v
Recycle Bin
        |
        +-- Restore
        |
        +-- Permanent Delete
```

---

# 10. API Policy

Existing backend API URLs remain unchanged.

No `/v2` namespace is introduced.

Frontend rewrite and backend API migration are independent tasks.

---

# 11. Migration Strategy

Phase 1:

- Create admin.html
- Create Admin application shell
- Create router and layout

Phase 2:

- Implement Telegram module
- Replace Dialog management
- Replace Source management

Phase 3:

- Implement Resources module
- Implement Scanner module

Phase 4:

- Implement Download
- Implement System
- Implement Recycle Bin

After migration:

- Remove old admin injection code
- Remove transitional global window dependencies

---

# Deferred Issues

## Source full scan optimization

Current behavior retained.

Every Source enable performs a full scan.

Optimization deferred.

## Download resume/retry bug

Independent backend issue.

## Admin frontend old implementation

The old admin.js injection model is not extended and will be removed after the new Admin application is complete.
