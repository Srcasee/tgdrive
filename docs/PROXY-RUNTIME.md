# Proxy Plugin

## Goal

Proxy is optional deployment infrastructure, not a core business feature. tgdrive is Telegram-only, but deployments may run in regions/networks where direct Telegram connectivity is unavailable or unreliable.

The deployment administrator decides whether proxy is enabled. Core must not contain country/region detection or hard-coded regional behavior.

## Architecture

```text
Core
  |
  v
Telegram client boundary
  |
  v
Connectivity decision
  |
  +---- direct
  |
  +---- proxy capability
            |
            v
       external proxy plugin
            |
       +---- SOCKS5
       +---- HTTP
       +---- other supported transports
       +---- optional sing-box runtime
```

The important boundary is that Core asks for connectivity configuration/capability; it does not import or implement a concrete proxy protocol.

## Deployment policy

Proxy selection is deployment/server-network configuration. The default deployment should use direct Telegram connectivity unless the administrator explicitly enables the proxy capability.

```text
Deployment A: direct
Deployment B: proxy
```

Account-scoped proxy selection is **not** a product requirement. Do not introduce account-level routing complexity unless a real deployment requires different Telegram accounts to use different network paths.

## Configuration

Direct mode:

```env
TG_PROXY_ENABLED=false
```

Proxy mode may expose a local SOCKS5 endpoint to Core:

```env
TG_PROXY_ENABLED=true
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
TG_PROXY_USERNAME=
TG_PROXY_PASSWORD=
```

The concrete proxy plugin may internally use SOCKS5, HTTP, sing-box or another supported mechanism. These implementation details must remain outside Core.

## Plugin contract

Plugins are discovered through the generic tgdrive plugin runtime. The proxy plugin advertises the `telegram.proxy` capability. Core should depend only on the generic plugin contract and capability lookup.

## Runtime reload boundary

`PluginRuntime.refresh()` reloads the plugin registry and increments a generation counter. Existing Telegram clients are intentionally not mutated in place. A proxy configuration change therefore requires an explicit safe client reconnect/rebuild operation before it affects active Telegram connections.

This is a lifecycle concern, not a reason to couple proxy implementation details into Telegram business logic.

## Security and operations

- Keep proxy credentials in deployment secrets/environment configuration, not in Telegram Resource metadata.
- Do not expose proxy credentials through Web APIs.
- Treat proxy availability/health as infrastructure state.
- Do not claim that a proxy bypasses Telegram service-side limits.
- Measure direct and proxied paths separately before making download-concurrency changes.
