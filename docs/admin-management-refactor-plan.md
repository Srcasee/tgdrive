# Admin Management Interface Refactor Plan v1

## Goal

Separate Telegram discovery, Source configuration, scanner runtime status, and resource management into independent management domains while keeping the existing Core architecture unchanged.

The refactor must preserve these boundaries:

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
Resources
```

Admin must not directly control Telegram discovery except through explicit reconciliation operations.

---

# 1. New Sidebar Structure

```text
Dashboard

Telegram
├── Accounts
├── Dialogs
├── Sources
└── Reconciliation

Resources
├── Resource browser
├── Categories
└── Recycle Bin

Downloads

System
└── Settings
```

---

# 2. Dialog Management

Purpose:

Display Telegram resources discovered by Dialog Discovery.

Responsibilities:

- show available channels
- show discovery status
- allow explicit reconciliation
- provide Source creation entry

Rules:

- Dialog page reads cached dialog data.
- Opening the page must not repeatedly trigger Telegram discovery.
- First initialization may use lazy discovery when no cache exists.
- Manual reconciliation remains explicit.

Dialog does not:

- start Scanner
- download files
- modify Resource state directly

---

# 3. Source Management

Purpose:

Manage which Telegram resources are scanned.

Responsibilities:

- enable Source
- disable Source
- view scan status
- trigger manual scan
- manage source metadata

Flow:

```text
Enable Source
      |
      v
SourceRepository
      |
      v
ScannerManager wakeup
      |
      v
Scanner
```

Enable/disable operations must not trigger Dialog Discovery.

---

# 4. Scanner Runtime View

New runtime-oriented view:

Display:

- active scanner tasks
- last scan time
- current Source state
- errors

This view is read-only for runtime state.

---

# 5. Resource Management

Resources page:

- browse catalog resources
- search
- classify
- batch operations

Resource management must remain independent from Telegram discovery.

---

# 6. Recycle Bin

Future implementation:

Delete operation flow:

```text
Delete Resource
      |
      v
Recycle Bin
      |
      +--> Restore
      |
      +--> Permanent delete
```

---

# 7. Frontend State Rules

Current known problem:

- Source enable/disable refreshes partial DOM state.
- Some refresh paths unnecessarily request Dialog data.

Target behavior:

```text
Dialog page
    |
    +--> dialog API

Source page
    |
    +--> source API

Runtime page
    |
    +--> scanner status API
```

No cross-domain implicit refresh.

---

# 8. Implementation Order

1. Separate Admin API responsibilities.
2. Separate Dialog and Source frontend state.
3. Add scanner runtime status view.
4. Remove unnecessary DOM refresh coupling.
5. Add batch Source/resource operations.
6. Add recycle bin workflow.
7. Add Topic classification support.

---

# Deferred Issues

## Source scanner full scan

Current behavior is intentionally retained:

- Source changes wake Scanner.
- Scanner performs a full enabled Source scan.

Optimization is deferred until correctness and Admin refactor are complete.

## Download stability

Download retry/resume improvements remain independent from Admin refactor.
