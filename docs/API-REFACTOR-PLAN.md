# TGDrive API Refactor Plan

## Goal

Refactor API organization by domain without changing existing URL paths.

The refactor is a code organization change, not an API version change. No `/v2` prefix will be introduced.

## Target domains

```
/api/telegram
    accounts
    dialogs
    sources
    sessions

/api/resources
    files
    categories

/api/scanner
    tasks
    logs
    settings

/api/download
    tasks
    history

/api/system
```

## Phase 1

Split `app/telegram/api.py` into domain routers while preserving:

```
/api/telegram/accounts
/api/telegram/accounts/{account_id}/dialogs
/api/telegram/sources
/api/telegram/reconnect
/api/telegram/reconcile
```

Target structure:

```
app/telegram/api/
    __init__.py
    accounts.py
    dialogs.py
    sources.py
    runtime.py
```

Responsibilities:

- accounts.py: Telegram account management
- dialogs.py: Dialog cache and discovery entry points
- sources.py: Telegram source configuration
- runtime.py: reconnect and reconciliation triggers

The business logic remains in existing repositories and services.

## Migration rules

- Keep URL compatibility.
- Keep Dialog as Telegram discovery data.
- Keep Source as Telegram-bound scan configuration.
- Do not let admin UI operations implicitly refresh unrelated domains.
