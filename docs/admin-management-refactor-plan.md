# Admin Management Interface Refactor Plan V3

## Goal

Replace the current mixed Admin injection model with an independent management application while preserving backend domain boundaries.

The refactor does not change Telegram lifecycle, scanner, catalog, ingestion, downloader or delivery architecture.

The Admin frontend becomes a control plane:

```text
Admin UI
   |
   +-- API
          |
          +-- Telegram domain
          +-- Resource domain
          +-- Scanner domain
          +-- Download domain
          +-- System domain
```

---

# 1. Current Problems

Current frontend contains two different models:

```text
index.html
 |
 +-- user resource UI
 |
 +-- inline javascript

admin.js
 |
 +-- Telegram panel injection
```

Problems:

- Admin UI lifecycle depends on the user page.
- Telegram modules depend on global window initialization order.
- Dialog refresh and Source operations were historically coupled.
- Adding new management domains would further increase coupling.

---

# 2. New Frontend Structure

Target:

```text
app/web/

├── index.html
│
├── admin.html
│
├── admin/
│   │
│   ├── app.js
│   ├── api.js
│   ├── router.js
│   ├── layout.js
│   │
│   ├── pages/
│   │   ├── dashboard.js
│   │   │
│   │   ├── telegram/
│   │   │   ├── accounts.js
│   │   │   ├── dialogs.js
│   │   │   └── sessions.js
│   │   │
│   │   ├── resources/
│   │   │   ├── sources.js
│   │   │   ├── files.js
│   │   │   └── categories.js
│   │   │
│   │   ├── scanner/
│   │   │   ├── tasks.js
│   │   │   ├── logs.js
│   │   │   └── settings.js
│   │   │
│   │   ├── download/
│   │   │   ├── active.js
│   │   │   └── history.js
│   │   │
│   │   ├── system/
│   │   │   ├── config.js
│   │   │   └── api.js
│   │   │
│   │   └── recycle-bin.js
```

---

# 3. Migration Principle

Do not introduce a frontend framework.

Use native JavaScript modules first.

Rules:

- One page owns one domain.
- One page refreshes only its own data.
- API calls are isolated in domain modules.
- No DOM manipulation across domains.

---

# 4. Telegram Dialogs

Dialogs represent Telegram discovery state.

Responsibilities:

- show discovered channels
- enable/disable Source configuration
- reconcile Telegram state

Dialogs do not own:

- scanner runtime
- download status
- resource lifecycle

Flow:

```text
Open Dialog page
        |
        v
Read Dialog API
        |
        v
User enables Source
        |
        v
Create Source
```

Browser refresh must not automatically trigger discovery.

---

# 5. Sources

Sources represent scanner configuration.

Flow:

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

Source actions refresh only Source page.

They do not reload Dialog discovery.

---

# 6. API Compatibility

Existing API URLs remain unchanged during migration.

No `/v2` API namespace.

Frontend migration and backend API migration are independent.

---

# 7. Migration Order

Phase 1:

- Add admin.html
- Add admin app shell
- Add router

Phase 2:

- Migrate Telegram Accounts
- Migrate Dialogs
- Migrate Sources

Phase 3:

- Scanner pages
- Download pages

Phase 4:

- Resource management
- Categories
- Recycle Bin

---

# Deferred Issues

## Source full scan optimization

Current behavior retained:

Every Source enable triggers a full scan.

Optimization deferred.

## Download resume/retry bug

Independent issue.

## Legacy admin.js

Keep temporarily as compatibility layer until Admin V3 migration completes.
