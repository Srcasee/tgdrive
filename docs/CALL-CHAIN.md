# Project Complete Call Chain

## Overview

This document describes the current runtime flow of tgdrive from deployment, Telegram authorization, dialog discovery, source configuration, scanning, ingestion, downloading, and delivery.

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

`ApplicationLifecycle` is responsible for application orchestration only:

- initialize PostgreSQL connection pool
- initialize database schema
- bootstrap admin account
- start runtime components
- shutdown runtime components

Core does not contain Telegram business logic.

## 2. Telegram Login and Runtime

First-time authentication:

```text
telegram/login.py
        |
        v
telegram/client.py
        |
        v
Telegram session creation
```

`login.py` is not part of every startup. It is mainly used for initial authorization and session generation.

Normal runtime:

```text
ApplicationLifecycle
        |
        v
telegram/client.py
        |
        v
Existing Telegram session
```

## 3. Dialog Discovery Flow

Dialog discovery is responsible for discovering available Telegram channels and making them available to the management interface.

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
        |
        v
Admin management interface
```

Important boundary:

- Dialog discovery discovers Telegram resources.
- Admin displays discovered dialogs.
- Refreshing the Admin page should read existing dialog data and should not automatically trigger Telegram discovery.

## 4. Dialog To Source Configuration

Dialog and Source are related but separate domains.

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

A Source represents a user-selected Telegram resource that should be scanned.

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
- send discovered resources into catalog/ingestion flow

Scanner does not perform dialog discovery.

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

Downloading happens after resource discovery.

```text
User download request
        |
        v
Delivery layer
        |
        v
downloader.py
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

## 8. Current Known Issues / Future Work

### Admin refresh coupling

Status: deferred.

Current issue:

- Enable/disable Source operations may trigger unnecessary Admin DOM refresh behavior.
- Management interface refactor will separate Dialog display, Source configuration, and runtime status views.

### Source scanner optimization

Status: deferred.

Current behavior:

- After Source changes, scanner correctness is prioritized by performing a full enabled Source scan.

Future optimization:

- Introduce incremental Source-level scanning events instead of full enabled Source reconciliation.
