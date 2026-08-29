# tgdrive Architecture

## Purpose

tgdrive indexes files uploaded to Telegram private groups/channels, stores metadata in PostgreSQL, and exposes searchable/downloadable files through a web API. Telegram sessions remain the source of file content; PostgreSQL is the metadata/index layer.

## Current architecture

```text
Browser
  |
  v
FastAPI
  +-- /files --------------------> FileRepository -> PostgreSQL
  +-- /api/telegram --------------> Account/Source repositories
  |
  +-- Telegram client manager ----> Telethon sessions
  |                                  |
  |                                  +--> ProxyManager -> proxy plugins
  |
  +-- Video stream service --------> chunk cache -> TelegramDownloader

Telegram private source
  -> scanner
  -> files table
  -> web listing/search
  -> download/stream from Telegram
```

### Main components

- `app/core/app.py`: application composition and lifecycle.
- `app/files/`: file listing, search, download and streaming HTTP APIs.
- `app/repositories/`: PostgreSQL persistence for files, accounts and sources.
- `app/telegram/`: Telethon client management, scanning and file downloading.
- `app/plugins/proxy/`: proxy plugin interface and entry-point based manager.
- `plugins/`: separately packaged plugins, currently including SOCKS5 proxy support.
- PostgreSQL: accounts, Telegram sources, file metadata, categories and share records.
- `app/web/`: browser UI.

## Implemented capabilities

### Telegram ingestion

1. Telegram session files are discovered under the configured session directory.
2. Sessions are synchronized into the `accounts` table.
3. Configured Telegram sources are scanned incrementally.
4. Media/file messages are indexed into PostgreSQL.
5. Files are uniquely identified by `(account_id, telegram_chat_id, message_id)`.
6. Scanner tracks source scan state and can mark unavailable/deleted files.

### Web file access

- Available file listing.
- Filename search using PostgreSQL `ILIKE`.
- File download through Telegram rather than duplicating the whole file locally.
- HTTP Range support for downloads/streaming.
- Video streaming with chunking, cache and prefetch support.

### Telegram proxy plugins

The core defines `ProxyPlugin.get_proxy()`. `ProxyManager` discovers installed packages through the `tgdrive.proxy` Python entry-point group. The current SOCKS5 plugin is an independent package under `plugins/tgdrive-proxy-socks5`.

This is plugin-based discovery at process startup. It is **not yet true runtime hot-plugging**: already-created Telegram clients do not automatically change proxy when a plugin/config changes.

### Categories

The PostgreSQL schema already contains `categories` and `files.category_id`, so the persistence model anticipates classification. The admin CRUD/API/UI workflow is not yet implemented.

## Target architecture

The intended architecture is a small core plus replaceable capability plugins:

```text
                         Web UI
                           |
                           v
                    API / Auth layer
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
        File Service   Admin Service  Media Manager
             |             |             |
             |             |        +----+----+----+
             |             |        |    |    |    |
             |             |      Video Image Audio ...
             |             |      plugin plugin plugin
             +-------------+-------------+
                           |
                       PostgreSQL
                           |
                  Telegram Client Manager
                           |
                     Proxy Manager
                           |
              +------------+------------+
              |            |            |
            direct       SOCKS5      future proxy
```

### Design rules

1. **Telegram is a content backend, not the web authentication system.** Web authentication and authorization must be explicit.
2. **Core code must depend on plugin interfaces, not concrete proxy/media implementations.**
3. **Proxy selection should eventually be scoped to a Telegram account/deployment, not only global environment variables.**
4. **Media handling should use a common plugin interface so video, images, audio and future handlers can be installed independently.**
5. **PostgreSQL remains the source of truth for indexed metadata and classification.**
6. **The web layer should not expose Telegram session credentials.**

## Planned plugin model

### ProxyPlugin

```text
ProxyPlugin
  name
  get_proxy()
```

Future implementations can be distributed independently and registered through `tgdrive.proxy`.

### MediaPlugin (target)

```text
MediaPlugin
  name
  can_handle(file_metadata)
  build_response(file_metadata, request_context)
```

A `MediaManager` should select the highest-priority compatible plugin. Video, image and audio handlers should not require changes to the core file API.

## Stage 1 architecture convergence

Stage 1 is focused on security and domain boundaries before adding more media features:

1. Introduce web authentication and authorization.
2. Separate admin operations from public file operations.
3. Implement category repository/service/API and admin UI boundary.
4. Ensure file/download/stream APIs enforce authorization consistently.
5. Keep Telegram session credentials internal and never return them through normal account APIs.
6. Add tests around auth, category ownership/permissions and protected file access.

## Known gaps / migration notes

- No complete web authentication/authorization layer currently protects the HTTP API.
- Category database schema exists, but admin category management is incomplete.
- Proxy plugins are discovered at startup rather than hot-loaded at runtime.
- Proxy configuration is currently process-wide rather than per Telegram account.
- Video streaming is implemented as a service directly used by the file API rather than a generic media plugin.
- Image online viewing and a generic media plugin manager are not implemented.
- Scanner full-sync semantics and failure-state handling require hardening before production use.

## Non-goals for Stage 1

- Do not redesign Telegram scanning unnecessarily.
- Do not replace PostgreSQL.
- Do not add media plugins before the core authentication/authorization and admin boundaries are stable.
