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

## 2. Configure Proxy before Telegram login when required

This ordering is mandatory for deployments that need a Telegram proxy. Do not perform a Telegram login first and configure the proxy only after a connection failure.

```text
./deploy.sh
  ↓
if proxy is required: edit .env + enable proxy
  ↓
docker compose --profile proxy up -d --build
  ↓
Telegram login
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

**Important:** `deploy.sh` creates `.env` if it does not exist and preserves an existing `.env`. The normal safe order is therefore `./deploy.sh` → proxy configuration → Telegram login. Do not put real proxy credentials into the repository or `.env.example`.

After changing proxy configuration, rebuild the Telegram clients explicitly:

```bash
# This endpoint requires an authenticated Web-admin session.
curl -X POST http://127.0.0.1:8080/api/telegram/reconnect
```

A full application restart is also sufficient.

## 3. Verify the base stack

```bash
docker compose ps
docker compose logs --tail=100 telegram-drive
```

Open:

```text
http://<server>:8080/
```

The normal service mounts the optional Proxy plugin only when the proxy profile is enabled. The Video plugin is not part of the Core runtime.

## 4. One-time Telegram login

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

## 5. Configure a Telegram Source — complete command flow

A Telegram Source is an **explicit administrator selection** of a Telegram chat to scan. The scanner does not ingest every dialog merely because the account is authorized.

The Source API is protected by the tgdrive Web-admin session cookie. Therefore, creating an empty `cookies.txt` and sending `-b cookies.txt` is **not** authentication. First log in to tgdrive itself and save the returned cookie with `-c cookies.txt`.

### 5.1 Log in to the tgdrive Web API

Use the Web-admin username/password configured in `.env`:

```bash
rm -f cookies.txt

curl -sS -c cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/auth/login \
  -d '{"username":"admin","password":"YOUR_ADMIN_PASSWORD"}'
```

Verify that the cookie is valid:

```bash
curl -sS -b cookies.txt http://127.0.0.1:8080/auth/me
```

Expected result contains the admin identity, for example:

```json
{"id":1,"username":"admin","role":"admin","enabled":true}
```

If your admin username is not `admin`, replace it in the login payload. Do not put the real password into Git or documentation.

### 5.2 Find the Telegram account ID

```bash
curl -sS \
  -b cookies.txt \
  http://127.0.0.1:8080/api/telegram/accounts
```

Find the object whose `name` is the Telegram account you logged in, for example `default`. Record its numeric `id` as `ACCOUNT_ID`.

For the current real-device test, `default` is account ID `1`.

### 5.3 List all Telegram dialogs for that account

Replace `1` below if your `default` account has a different database ID:

```bash
curl -sS \
  -b cookies.txt \
  http://127.0.0.1:8080/api/telegram/accounts/1/dialogs
```

The response lists dialogs with their numeric Telegram IDs and names. **Choose the target by numeric ID**, not by name alone, because Telegram dialog names are not unique.

For example, the current real-device test contains:

```text
My Documents  -> -1004413553797
Documents     -> -1004368336866
```

### 5.4 Add the selected dialog as a Telegram Source

Replace the values with the account ID and Telegram chat ID selected above:

```bash
curl -sS \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/api/telegram/sources \
  -d '{"account_id":1,"telegram_chat_id":-1004413553797,"name":"My Documents"}'
```

This creates an enabled source. It does not require manually entering a Telegram username or invite link.

### 5.5 Verify the Source in PostgreSQL

```bash
docker compose exec postgres psql \
  -U tgdrive \
  -d tgdrive \
  -c 'SELECT id, account_id, telegram_chat_id, name, enabled, last_message_id FROM telegram_sources ORDER BY id;'
```

The selected source should show `enabled = t`. `last_message_id` starts at `0` for a new source and advances as messages are indexed.

### 5.6 Verify scanner activity

```bash
docker compose logs --tail=200 telegram-drive | grep -E '\[SCAN\]|\[TG\]'
```

A healthy source scan includes output similar to:

```text
[SCAN] starting: default
[SCAN] dialog: My Documents id: -1004413553797
[SCAN] finished N files
[SCAN] sleep 300s
```

Then verify indexed records:

```bash
docker compose exec postgres psql \
  -U tgdrive \
  -d tgdrive \
  -c 'SELECT id, filename, size, telegram_chat_id, message_id, topic_id, account_id, scan_status, is_available FROM files ORDER BY id DESC LIMIT 20;'
```

The scanner is metadata-first: it records Telegram message/file metadata without downloading the complete file merely to build the catalog.

## 6. Verify scanning and catalog

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
