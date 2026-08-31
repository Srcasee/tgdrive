# Quick Start

## Goal

Get a fresh Docker host from zero to a working Telegram-backed tgdrive with one base bootstrap command and no manual PostgreSQL setup.

## 1. Fresh-server bootstrap

Prerequisites:

- Linux server with Docker Engine and Docker Compose plugin.
- Telegram `api_id` and `api_hash` from `my.telegram.org`.
- A Telegram account that can authorize the application.

Clone and bootstrap the base system:

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
./deploy.sh
```

When `.env` does not exist, `deploy.sh` prompts for the Telegram API ID/hash and Web admin password, generates `AUTH_SECRET` and the PostgreSQL password, creates persistent data directories, validates Compose, and starts PostgreSQL + Core. It does **not** authorize a Telegram account and does **not** enable/configure the optional proxy.

For unattended base bootstrap, provide `TG_API_ID`, `TG_API_HASH` and `ADMIN_PASSWORD` in the environment before running `./deploy.sh`. `TG_PHONE` is not required by the current deployment script because Telegram accounts are authorized explicitly afterward. An existing `.env` is never overwritten.

## 2. Verify the base stack

```bash
docker compose ps
docker compose logs --tail=100 telegram-drive
```

Open:

```text
http://<server>:8080/
```

The normal service mounts the optional Proxy plugin only when the proxy profile is enabled. The Video plugin is not part of the Core runtime.

## 3. One-time Telegram login

Use an explicit account name:

```bash
./login-account.sh default +1234567890
```

A second account can use a different name:

```bash
./login-account.sh Asada +861234567890
```

The resulting sessions are `/data/accounts/default.session` and `/data/accounts/Asada.session`. Account naming is intentional; do not rename sessions to change application behavior.

The Telethon session is reused by the application. Multiple account names may be configured independently.

`login-account.sh` is only a deployment convenience wrapper; `app/telegram/login.py` is the single login implementation.

## 4. Configure a Telegram source

Log in as the Web administrator and use the Telegram management API/UI to discover dialogs. Select the exact Telegram chat by numeric chat ID; display names are not unique.

Create/enable a source for the selected chat. The scanner only processes explicitly configured Telegram sources.

Example source used in the current real-device test:

```text
account: default
chat: My Documents
chat id: -1004413553797
```

## 5. Optional proxy — recommended after deploy.sh

Proxy is optional and deployment-controlled. The recommended order is:

```text
./deploy.sh
  ↓
configure Telegram account(s)
  ↓
configure source(s)
  ↓
if network requires proxy: configure .env + enable proxy
```

Edit `.env` and configure the proxy values, then start the proxy profile:

```bash
# edit .env first
# set TG_PROXY_ENABLED=true and configure TG_PROXY_*
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

**Important:** proxy can technically be prepared before `deploy.sh` by creating a complete `.env` first; `deploy.sh` preserves an existing `.env`. Do not put real proxy credentials into the repository or `.env.example`. If no `.env` exists, let `deploy.sh` create it first, then configure the proxy.

After changing proxy configuration, rebuild the Telegram clients explicitly:

```bash
curl -X POST http://127.0.0.1:8080/api/telegram/reconnect
```

The endpoint requires administrator authentication. A full application restart is also sufficient.

## 6. Verify scanning and catalog

The scanner indexes Telegram metadata only. It does not download complete files during scanning.

Check the service log:

```bash
docker compose logs --tail=150 telegram-drive | grep -E '\[SCAN\]|\[TG\]'
```

Catalog:

```bash
curl -sS 'http://127.0.0.1:8080/catalog?page=1&size=50'
```

Search:

```bash
curl -sS 'http://127.0.0.1:8080/catalog/search?q=example'
```

The current real-device test has verified catalog browsing, filename search, category filtering, category creation and category deletion.

## 7. Verify Resource delivery

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

A complete non-range delivery also verifies the emitted content with SHA-256 and promotes the physical source to its canonical Resource identity; this promotion still needs explicit real-device validation.

## 8. Verify sharing

```text
POST /resources/<resource-id>/share
GET  /share/<token>
```

The current real-device test has verified share-link generation, visible concrete link, administrator deletion and shared download.

## 9. Current real-device test plan

Completed:

```text
1. Core + PostgreSQL health
2. Telegram login/session reuse
3. Explicit source configuration
4. Metadata-only incremental scan
5. Resource catalog/search/classification
6. Share-link lifecycle
7. Basic Resource download
```

Pending:

```text
8. Download chain benchmark and transport diagnosis
9. Multi-account failover
10. HTTP Range behavior on a large real file
11. Complete-download SHA-256 promotion
12. Proxy connectivity/reconnect smoke test
13. Large-file behavior above Telegram per-file limits
14. Telegram Topic recognition + Topic → Category mapping
15. Batch Resource classification
```

Video is intentionally excluded.

## Recovery

To force a fresh login for one account, stop Core first and remove only that account's session file from the mounted data directory:

```bash
docker compose stop telegram-drive
rm -f ./data/accounts/<account_name>.session
./login-account.sh <account_name> <phone>
docker compose up -d telegram-drive
```

Do not delete the PostgreSQL volume just to re-authenticate Telegram.
