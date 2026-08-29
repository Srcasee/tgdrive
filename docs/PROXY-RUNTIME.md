# Proxy Runtime

## Goal

Proxy is deployment infrastructure, not a Core feature. TGDrive makes no assumption about server geography. Direct connectivity is the default; a deployment explicitly enables a proxy when its network requires one.

## Architecture

```text
Core / File services
        |
        v
Telegram client boundary
        |
        v
ProxyRuntime (plugin layer)
   |            |
   v            v
 none        socks5 / external plugins
```

The Core does not decide whether China, Europe, the US, or another region needs a proxy. That is deployment configuration.

## Configuration

Direct mode (default):

```env
TG_PROXY_ENABLED=false
```

SOCKS5 mode:

```env
TG_PROXY_ENABLED=true
TG_PROXY_PLUGIN=socks5
TG_PROXY_HOST=127.0.0.1
TG_PROXY_PORT=1080
TG_PROXY_USERNAME=
TG_PROXY_PASSWORD=
```

A per-account plugin override can be supplied with a normalized session name, for example:

```env
TG_PROXY_ACCOUNT_A_PLUGIN=none
```

The password is read from the process environment and is never returned by the runtime API.

## Plugin contract

Implement `ProxyPlugin.get_proxy()` and register an external implementation through the `tgdrive.proxy` entry-point group. The plugin returns the Telethon proxy configuration or `None`.

## Hot reload boundary

`ProxyRuntime.refresh()` reloads the provider registry and increments a generation counter. Existing Telegram clients are intentionally not mutated in place. Reconnecting/replacing a client is a separate lifecycle operation so proxy changes cannot corrupt an active transfer.

## Phase 2 direction

Before high-speed download tuning, benchmark the actual deployment route. Proxy runtime will remain independent from DownloadManager, chunk scheduling, cache, and future Media plugins.
