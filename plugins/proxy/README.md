# Telegram proxy plugin

This plugin is optional deployment infrastructure. tgdrive does not detect regions or embed proxy protocol logic in core code.

## Run the proxy service on a real server

Build the plugin image:

```bash
docker build -t tgdrive-proxy ./plugins/proxy
```

For a VLESS upstream, provide at least:

```text
TG_PROXY_TYPE=socks5
TG_PROXY_PORT=1080
TG_PROXY_UPSTREAM_TYPE=vless
TG_PROXY_VLESS_SERVER=<server>
TG_PROXY_VLESS_PORT=443
TG_PROXY_VLESS_UUID=<uuid>
TG_PROXY_VLESS_SERVER_NAME=<sni>
TG_PROXY_VLESS_WS_PATH=/
TG_PROXY_VLESS_WS_HOST=<optional-host>
```

Start the proxy container with port `1080` exposed to the tgdrive application host. `sing-box check` is executed before the proxy process starts, so an invalid generated configuration fails immediately.

## Test the actual Telegram path

After the proxy is reachable from the tgdrive runtime, run:

```bash
TG_PROXY_ENABLED=true \
TG_PROXY_TYPE=socks5 \
TG_PROXY_HOST=<proxy-host> \
TG_PROXY_PORT=1080 \
TG_PROXY_TEST_SESSION=proxy-smoke \
python scripts/test_telegram_proxy.py
```

The smoke test creates a real Telethon `TelegramClient` with the same proxy object used by tgdrive and calls `get_me()`. It therefore verifies the complete path:

```text
tgdrive -> proxy plugin -> local proxy -> configured upstream -> Telegram API
```

The smoke test requires valid `TG_API_ID`, `TG_API_HASH`, and an authorized Telethon session. It is intentionally not part of CI because it requires deployment-specific credentials and a real network path.
