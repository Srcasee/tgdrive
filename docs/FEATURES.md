# Features and Target Capabilities

## Current

| Capability | Status | Notes |
|---|---|---|
| Telegram private-source scanning | Implemented | Telethon sessions + source scanner |
| PostgreSQL file index | Implemented | Metadata, availability and scan state |
| Web file listing | Implemented | Available files |
| Filename search | Implemented | Basic `ILIKE` search |
| Download | Implemented | Streaming from Telegram |
| HTTP Range | Implemented | Used by download/stream paths |
| Video streaming | Implemented | Chunking/cache/prefetch service |
| Multi-account Telegram clients | Implemented | Session/account mapping |
| Proxy entry-point plugins | Implemented | `tgdrive.proxy` group |
| SOCKS5 proxy plugin | Implemented | Separate package |
| Category schema | Partial | DB schema exists |
| Admin category management | Not implemented | Requires auth + admin API/UI |
| Web authentication | Not implemented | Critical Stage 1 item |
| Image online viewer | Not implemented | Future media plugin |
| Generic media plugin manager | Not implemented | Future architecture |
| Runtime proxy hot-plug | Not implemented | Current discovery is startup-only |

## Target user workflow

```text
Admin configures Telegram account/session
       -> adds private Telegram source
       -> scanner indexes messages/files
       -> metadata enters PostgreSQL
       -> web user authenticates
       -> searches/browses files
       -> downloads or opens a compatible media viewer
```

## Target administration workflow

```text
Admin login
  -> category CRUD
  -> assign category to one/many files
  -> filter/search by category
  -> manage Telegram accounts/sources
  -> view scan status/errors
```

## Target plugin workflow

```text
Core
  -> PluginManager
      -> ProxyPlugin(s)
      -> MediaPlugin(s)

A deployment installs only the plugins it needs.
Core APIs remain stable when a new proxy or media handler is added.
```
