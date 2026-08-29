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
  |                                  +--> PluginRuntime -> optional capabilities
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
- `app/plugins/`: generic plugin contract and entry-point based runtime.
- `plugins/`: separately packaged optional plugins, currently including the proxy capability plugin.
- PostgreSQL: accounts, Telegram sources, file metadata, categories and share records.
- `app/web/`: browser UI.

## Plugin architecture

The Core exposes one generic plugin API. Plugins advertise capabilities and are discovered through the `tgdrive.plugins` Python entry-point group.

```text
app/plugins/
  interface.py      generic Plugin contract
  runtime.py        discovery + capability lookup

plugins/
  proxy/            optional network proxy capability
    tgdrive_proxy.py
    sing-box/       optional proxy runtime implementation
```

The Core does not import a concrete plugin package. If the proxy plugin is not installed, Telegram clients use a direct connection. If it is installed and enabled, the Telegram client boundary asks the generic `PluginRuntime` for the `telegram.proxy` capability.

### Proxy capability

The proxy plugin is deliberately not named after a protocol. It may implement SOCKS5, HTTP and future proxy protocols internally. Its current Telethon adapter supports SOCKS5/SOCKS5H and HTTP endpoints; sing-box can provide a local SOCKS5 endpoint backed by VLESS, or another supported upstream in the future.

Server geography is deployment configuration, not application logic. Core behavior is identical across regions.

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
                     Generic PluginRuntime
                           |
                 +---------+----------+
                 |                    |
          telegram.proxy         future capabilities
                 |
            proxy plugin
             /       \
         SOCKS5      HTTP / future
```

### Design rules

1. **Telegram is a content backend, not the web authentication system.** Web authentication and authorization must be explicit.
2. **Core code must depend on generic plugin interfaces, not concrete proxy/media implementations.**
3. **Proxy selection is deployment configuration and may later be scoped to a Telegram account without changing the plugin framework.**
4. **Media handling should use a common plugin interface so video, images, audio and future handlers can be installed independently.**
5. **PostgreSQL remains the source of truth for indexed metadata and classification.**
6. **The web layer should not expose Telegram session credentials.**

## Plugin model

### Generic Plugin

```text
Plugin
  name
  version
  capabilities
```

Plugins are distributed under `plugins/` and registered through `tgdrive.plugins`.

### Proxy capability

```text
proxy plugin
  capabilities: telegram.proxy
  get_proxy(account_name)
```

The proxy plugin can select its concrete transport internally without requiring changes to Core.

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
- Plugins are discovered at startup rather than hot-loaded at runtime.
- Proxy configuration is currently process-wide rather than per Telegram account.
- Video streaming is implemented as a service directly used by the file API rather than a generic media plugin.
- Image online viewing and a generic media plugin manager are not implemented.
- Scanner full-sync semantics and failure-state handling require hardening before production use.

## Non-goals for Stage 1

- Do not redesign Telegram scanning unnecessarily.
- Do not replace PostgreSQL.
- Do not add media plugins before the core authentication/authorization and admin boundaries are stable.
