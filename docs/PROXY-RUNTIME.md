# Proxy Plugin

## Goal

Proxy is optional deployment infrastructure, not a Core feature. TGDrive makes no assumption about server geography. Direct connectivity is the default; a deployment explicitly enables the proxy plugin when its network requires one.

## Architecture

```text
Core / File services
        |
        v
Telegram client boundary
        |
        v
Generic PluginRuntime
        |
        +---- no proxy capability -> direct connection
        |
        +---- proxy plugin
                 |
                 +---- SOCKS5
                 +---- HTTP
                 +---- future proxy protocols
                 +---- optional sing-box runtime
```

The Core does not decide whether China, Europe, the US, or another region needs a proxy. That is deployment configuration.

## Configuration

Direct mode:

```env
TG_PROXY_ENABLED=false
```

Proxy plugin using a local SOCKS5 endpoint:

```env
TG_PROXY_ENABLED=true
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
TG_PROXY_USERNAME=
TG_PROXY_PASSWORD=
```

The same plugin can expose an HTTP proxy endpoint by setting `TG_PROXY_TYPE=http`. Additional protocols can be implemented inside the proxy plugin without changing Core.

## Plugin contract

Plugins register through the generic `tgdrive.plugins` entry-point group. The proxy plugin advertises the `telegram.proxy` capability. Core imports only `app.plugins.Plugin` and `app.plugins.PluginRuntime`; it does not import a proxy implementation or a concrete proxy protocol.

## Optional sing-box profile

The Compose `proxy` profile runs sing-box only when the deployment enables it. Its configuration lives inside `plugins/proxy/sing-box/`, so sing-box is an implementation detail of the proxy plugin rather than a Core-level service.

## Hot reload boundary

`PluginRuntime.refresh()` reloads the plugin registry and increments a generation counter. Existing Telegram clients are intentionally not mutated in place. Reconnecting/replacing a client is a separate lifecycle operation so plugin changes cannot corrupt an active transfer.

## Deployment principle

A deployment decides whether to enable the proxy profile. Core behavior remains identical across regions, and future plugins can be added under `plugins/` without introducing feature-specific plugin logic into `app/plugins/`.
