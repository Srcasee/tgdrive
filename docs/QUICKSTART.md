# Quick Start

## Goal

Get a fresh Debian/Docker host from zero to a working Telegram-backed tgdrive with the fewest manual steps.

## 1. Configure

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
cp .env.example .env
```

Set only the required values first:

- `TG_API_ID`
- `TG_API_HASH`
- `TG_PHONE`
- `AUTH_SECRET`

The default deployment uses PostgreSQL from Compose and the built-in proxy runtime. Proxy settings can remain disabled unless Telegram connectivity requires them.

## 2. Start

```bash
docker compose up -d --build
```

Check:

```bash
docker compose ps
docker compose logs --tail=100 telegram-drive
```

## 3. One-time Telegram login

```bash
docker compose exec telegram-drive python -m telegram.login
```

Complete the Telegram code/2FA prompts when requested. The resulting Telethon session is stored in `/data/accounts/default.session` and is reused by the application.

If the session already exists and is authorized, no new login is required.

## 4. Verify account

Open the web UI or call:

```bash
curl -sS -b /tmp/tgdrive-cookie.jar \
  http://127.0.0.1:8080/api/telegram/accounts
```

The application automatically discovers `.session` files and creates the corresponding account row. Manual SQL is not part of the normal setup.

## 5. Select a source

Use the account dialog API/UI to select the exact Telegram chat. Always use the numeric chat ID; display names are not unique.

Create the source through the API/UI. The scanner only scans explicitly configured `telegram_sources` rows.

## 6. Verify files

```bash
curl -sS -b /tmp/tgdrive-cookie.jar \
  'http://127.0.0.1:8080/files?page=1&size=50'
```

For an MP4, verify Range support before investigating performance:

```bash
curl -sS -D - -o /dev/null \
  -b /tmp/tgdrive-cookie.jar \
  -H 'Range: bytes=0-1048575' \
  http://127.0.0.1:8080/files/<file-id>/stream
```

Expected response: `206 Partial Content` with a correct `Content-Range`.

## Proxy mode

The application has one proxy implementation path. Enable it with:

```text
TG_PROXY_ENABLED=true
TG_PROXY_PLUGIN=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
```

Do not use the old `ENABLE_PROXY`, `PROXY_HOST`, `PROXY_PORT`, or `PROXY_TYPE` variables.

## Recovery

To force a fresh Telegram login, stop Core first and remove only the intended session file:

```bash
docker compose stop telegram-drive
docker compose exec telegram-drive sh -c 'rm -f /data/accounts/default.session'
docker compose start telegram-drive
docker compose exec telegram-drive python -m telegram.login
```

Do not delete the PostgreSQL volume just to re-authenticate Telegram.
