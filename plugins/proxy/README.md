# Telegram proxy plugin

This plugin is optional deployment infrastructure. tgdrive does not detect regions or embed proxy protocol logic in core code.

## Production deployment

The proxy runs as a separate Compose service under the `proxy` profile. The main application discovers the plugin from the mounted `plugins/` directory and uses its `telegram.proxy` capability when `TG_PROXY_ENABLED=true`.

For a deployment that requires the proxy:

```bash
docker compose --project-name tgdrive --profile proxy up -d --build
```

The application reaches the proxy through the Compose network at `proxy:1080` by default. Do not publish the proxy port to the public internet unless there is a specific operational need.

## VLESS upstream

Provide at least:

```text
TG_PROXY_ENABLED=true
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
TG_PROXY_UPSTREAM_TYPE=vless
TG_PROXY_VLESS_SERVER=<server>
TG_PROXY_VLESS_PORT=443
TG_PROXY_VLESS_UUID=<uuid>
TG_PROXY_VLESS_SERVER_NAME=<sni>
TG_PROXY_VLESS_WS_PATH=/
TG_PROXY_VLESS_WS_HOST=<optional-host>
```

`TG_PROXY_VLESS_WS_HOST` is optional. When supplied, it is sent as the WebSocket `Host` header; `TG_PROXY_VLESS_SERVER_NAME` remains the TLS SNI.

The plugin generates the sing-box configuration at runtime and executes `sing-box check` before starting the proxy. An invalid generated configuration therefore fails before the proxy begins accepting connections.

## Test the actual Telegram path

After the proxy container is running and the main application has the proxy plugin mounted, run the real-server smoke test from the application container:

```bash
docker compose --project-name tgdrive exec telegram-drive python scripts/proxy_smoke.py
```

The smoke test creates a real Telethon `TelegramClient` with the same proxy object used by tgdrive and calls `get_me()`. It therefore verifies the complete path:

```text
tgdrive -> proxy plugin -> local proxy -> configured upstream -> Telegram API
```

The smoke test requires valid `TG_API_ID`, `TG_API_HASH`, and an authorized Telethon session. It is intentionally not part of CI because it requires deployment-specific credentials and a real network path.
