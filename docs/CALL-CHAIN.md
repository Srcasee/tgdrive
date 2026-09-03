# Project Complete Call Chain

## Overview

This document describes the current runtime flow of tgdrive from deployment, Telegram authorization, dialog discovery, Source configuration, scanning, ingestion, downloading, and delivery.

## 1. Deployment and Application Startup

```text
./deploy.sh
    |
    v
Container startup
    |
    v
app/main.py
    |
    v
app/core/lifecycle.py
```

`ApplicationLifecycle` is application orchestration only:

- initialize PostgreSQL connection pool
- initialize database schema
- bootstrap admin account
- start and stop runtime components

Core does not contain Telegram business logic.

## 2. Telegram Login and Runtime

First-time authorization:

```text
telegram/login.py
        |
        v
telegram/client.py
        |
        v
Telegram session creation
```

`login.py` is only used for initial account authorization. Normal startup reuses existing sessions.

Runtime:

```text
ApplicationLifecycle
        |
        v
telegram/client.py
        |
        v
Existing Telegram sessions
```

## 3. Dialog Discovery Flow

Dialog Discovery maintains the Telegram dialog metadata cache.

```text
Telegram Client
        |
        v
telegram/dialog_discovery.py
        |
        v
Telegram dialogs
        |
        v
dialog repository
        |
        v
dialogs table
```

Current behavior:

- Runtime reconciliation can refresh dialogs.
- The Admin Dialog view reads cached dialog data.
- First Admin Dialog access may lazily initialize discovery when no dialog cache exists.
- After initialization, normal page refreshes only read the dialogs table.
- Explicit reconciliation remains the manual discovery trigger.

Dialog Discovery does not create Sources and does not start Scanner.

## 4. Dialog and Source Boundary

Dialog and Source are separate domains.

```text
Dialog Discovery
        |
        v
dialogs table

Admin selects dialog
        |
        v
Source configuration
        |
        v
sources table
```

A Source represents an administrator-selected Telegram resource that Scanner is allowed to process.

## 5. Source Scanner Flow

```text
SourceRepository
        |
        v
ScannerManager
        |
        v
telegram/scanner.py
        |
        v
Telegram message API
        |
        v
File message processing
```

Scanner responsibilities:

- read enabled Sources
- scan Telegram messages
- extract file metadata
- submit resources to catalog/ingestion

Scanner does not perform Dialog Discovery.

Current Source change behavior:

- Source changes wake Scanner immediately.
- Scanner currently performs a full enabled Source scan for correctness.
- Incremental Source scanning is deferred.

## 6. Catalog and Ingestion Flow

```text
scanner.py
    |
    v
Catalog layer
    |
    v
Ingestion layer
    |
    v
Resource metadata and state management
```

## 7. Download and Delivery Flow

```text
User download request
        |
        v
Delivery layer
        |
        v
telegram/downloader.py
        |
        v
Telegram file download API
        |
        v
Downloaded file
        |
        v
Delivery response
```

## 8. Deferred Issues

### Admin refresh coupling

Status: deferred for Admin refactor.

Current issue:

- Source enable/disable operations may refresh unnecessary Dialog UI DOM state.
- Dialog display, Source configuration, and runtime status should become separate Admin views.

### Source scanner optimization

Status: deferred.

Current behavior:

- Correctness is prioritized by full enabled Source reconciliation after Source changes.

Future:

- Incremental Source-level scanning events.
