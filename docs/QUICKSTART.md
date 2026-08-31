# Quick Start

## Goal

Get a fresh Docker host from zero to a working Telegram-backed tgdrive with the fewest manual steps.

## 1. Configure

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
cp .env.example .env
```

Set the required values:

- `TG_API_ID`
- `TG_API_HASH`
- `TG_PHONE`
- `AUTH_SECRET`

Direct Telegram connectivity is the default. Do not configure a proxy unless the server/network actually needs one.

## 2. Start the core stack

```bash
docker compose up -d --build
```

Check:

```bash
docker compose ps
docker compose logs --tail=100 telegram-drive
```

The normal service mounts only the optional Proxy plugin. The Video plugin is not part of the Core runtime.

## 3. One-time Telegram login

Use the account-named login helper:

```bash
./login-account.sh default +1234567890
```

Or invoke the module directly:

```bash
docker compose run --rm \
  -e TG_PHONE="+1234567890" \
  -e TG_ACCOUNT_NAME="default" \
  telegram-drive \
  python3 /app/telegram/login.py
```

Complete the Telegram code/2FA prompts when requested.

The Telethon session is stored under `/data/accounts/<account_name>` by default and is reused by the application. Multiple account names may be configured independently.

## 4. Verify the application

Open:

```text
http://<server>:8080/
```

The Resource-first Web UI supports catalog browsing/search, download, share links and administrator Resource classification. No manual PostgreSQL SQL or account-row creation is required for the normal bootstrap.

## 5. Configure a Telegram source

Use the authenticated Telegram management API/UI to discover dialogs and select the exact Telegram chat. Use the numeric Telegram chat ID; display names are not unique.

Create/enable a source for the chat. The scanner only processes explicitly configured Telegram sources.

## 6. Verify the Resource catalog

The active catalog API is Resource-centric:

```bash
curl -sS http://127.0.0.1:8080/catalog?page=1\&size=50
```

Search:

```bash
curl -sS 'http://127.0.0.1:8080/catalog/search?q=example'
```

The scanner indexes Telegram metadata only. It does not download complete files during the scan.

## 7. Verify delivery

A Resource is delivered through its Resource ID:

```text
GET /resources/<resource-id>/download
GET /resources/<resource-id>/stream
```

For Range behavior:

```bash
curl -sS -D - -o /dev/null \
  -H 'Range: bytes=0-1048575' \
  http://127.0.0.1:8080/resources/<resource-id>/stream
```

Expected response: `206 Partial Content` with a correct `Content-Range`.

Delivery selects among available Telegram backing locations. If the first location is unavailable before transfer begins, another usable Telegram account/location can be selected.

## Optional proxy deployment

Only enable the proxy profile when the server's network requires it.

Set the proxy environment values in `.env`, then start:

```bash
docker compose --profile proxy up -d --build
```

Typical local proxy endpoint values are:

```env
TG_PROXY_ENABLED=true
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
```

The external proxy plugin may use a sing-box upstream. Core does not contain region detection or proxy protocol logic.

After changing proxy configuration, restart/recreate tgdrive so existing Telegram clients are rebuilt with the new connectivity settings. Explicit reconnect lifecycle remains tracked separately.

## Video

Video playback/chunk caching is outside the current real-device testing scope. The optional plugin is kept outside the Core delivery path and is not mounted by the normal service.

## Recovery

To force a fresh login for one account, stop Core first and remove only that account's session path:

```bash
docker compose stop telegram-drive
docker compose exec telegram-drive sh -c 'rm -f /data/accounts/<account_name>.session'
docker compose start telegram-drive
./login-account.sh <account_name> <phone>
```

Do not delete the PostgreSQL volume just to re-authenticate Telegram.
