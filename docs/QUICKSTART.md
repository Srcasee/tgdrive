# Quick Start

## Goal

Get a fresh Docker host from zero to a working Telegram-backed tgdrive without manually configuring PostgreSQL. Telegram authorization automatically discovers and caches dialog metadata, but **only administrator-selected Telegram Sources are scanned for messages/files**.

## 1. Fresh-server bootstrap

```bash
git clone https://github.com/Srcasee/tgdrive.git
（无法访问Github使用镜像代理
git clone https://gh-proxy.com/https://github.com/Srcasee/tgdrive.git
git clone https://gh-proxy.com/https://github.com/Srcasee/tgdrive.git）
cd tgdrive
./deploy.sh
```

`deploy.sh` bootstraps Docker, persistent directories, `.env`, secrets, Compose validation, Core and PostgreSQL. It does not authorize Telegram or configure the optional proxy.

## 2. Configure Proxy before Telegram login when required

```text
./deploy.sh
  ↓
if proxy is required: edit .env + enable proxy
  ↓
docker compose --profile proxy up -d --build
  ↓
Telegram login
```

Configure `TG_PROXY_ENABLED=true` and `TG_PROXY_*` before the first Telegram login. Never put real proxy credentials in Git or `.env.example`.

## 3. Verify the base stack

```bash
docker compose ps
docker compose logs --tail=100 telegram-drive
```

Open `http://<server>:8080/`.

## 4. One-time Telegram login

```bash
./login-account.sh default +1234567890
./login-account.sh Asada +861234567890
```

The account name is the session basename, e.g. `/data/accounts/default.session`. Sessions are reused by Core.

**Immediately after successful authorization, Core automatically iterates the account's Telegram dialogs and persists metadata. This is metadata discovery only; it does not iterate messages or download files.**

## 5. Configure a Telegram Source — complete command flow

The required architecture is:

```text
TG login
  ↓
automatically discover ALL Dialogs
  ↓
persist/refresh Dialog metadata only
  ↓
admin views Dialogs
  ↓
admin selects target group/channel
  ↓
create Telegram Source
  ↓
scanner reads ONLY enabled Sources
```

An authorized account therefore **must not** cause all Telegram conversations to be scanned.

### 5.1 Log in to the tgdrive Web API

The Source API requires the Web-admin cookie. First create a valid cookie jar with `-c`; using `-b cookies.txt` before login returns `401 authentication required`.

```bash
rm -f cookies.txt
curl -sS -c cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/auth/login \
  -d '{"username":"admin","password":"YOUR_ADMIN_PASSWORD"}'

curl -sS -b cookies.txt http://127.0.0.1:8080/auth/me
```

### 5.2 Find the Telegram account ID

```bash
curl -sS -b cookies.txt \
  http://127.0.0.1:8080/api/telegram/accounts
```

Find the account object for `default` and record its numeric `id`. The current real-device test uses `1`.

### 5.3 List the automatically discovered Telegram dialogs

This endpoint reads the persisted dialog metadata cache. It does **not** trigger message scanning.

```bash
curl -sS -b cookies.txt \
  http://127.0.0.1:8080/api/telegram/accounts/1/dialogs
```

Choose the target using its numeric Telegram ID. Names are not guaranteed to be unique. Current test examples include:

```text
My Documents  -> -1004413553797
Documents     -> -1004368336866
```

### 5.4 Add ONLY the selected dialog as a Telegram Source

```bash
curl -sS -b cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/api/telegram/sources \
  -d '{"account_id":1,"telegram_chat_id":-1004413553797,"name":"My Documents"}'
```

Creating this Source is the explicit administrative authorization for that chat to be scanned. No other dialog becomes a Source automatically.

### 5.5 Verify the Source

```bash
docker compose exec postgres psql -U tgdrive -d tgdrive \
  -c 'SELECT id, account_id, telegram_chat_id, name, enabled, last_message_id FROM telegram_sources ORDER BY id;'
```

### 5.6 Verify that scanning is Source-scoped

```bash
docker compose logs --tail=200 telegram-drive | grep -E '\[SCAN\]|\[TG\]'
```

Expected behavior is that scanner lines appear only for enabled Sources, e.g.:

```text
[SCAN] starting: default
[SCAN] dialog: My Documents id: -1004413553797
[SCAN] finished N files
```

There must be no `[SCAN] dialog:` line for unconfigured dialogs merely because they appeared in the account's dialog list.

Verify indexed records:

```bash
docker compose exec postgres psql -U tgdrive -d tgdrive \
  -c 'SELECT id, filename, size, telegram_chat_id, message_id, topic_id, account_id, scan_status, is_available FROM files ORDER BY id DESC LIMIT 20;'
```

The scanner is metadata-first and does not download complete Telegram files merely to build the catalog.

## 6. Verify scanning and catalog

```bash
curl -sS 'http://127.0.0.1:8080/catalog?page=1&size=50'
curl -sS 'http://127.0.0.1:8080/catalog/search?q=example'
```

## 7. Verify Resource delivery

```text
GET /resources/<resource-id>/download
GET /resources/<resource-id>/stream
```

Range test:

```bash
curl -sS -D - -o /dev/null \
  -H 'Range: bytes=0-1048575' \
  http://127.0.0.1:8080/resources/<resource-id>/stream
```

## 8. Verify sharing

```text
POST /resources/<resource-id>/share
GET  /share/<token>
```

## 9. Current real-device test plan

Completed:

```text
1. Core + PostgreSQL health
2. Telegram login/session reuse
3. Explicit Telegram Source configuration
4. Metadata-only incremental scan
5. Resource catalog/search/classification
6. Share-link lifecycle
7. Basic Resource download
```

Pending:

```text
8. Automatic complete Dialog metadata discovery/cache real-device verification
9. Download chain benchmark and transport diagnosis
10. Multi-account failover
11. HTTP Range behavior on a large real file
12. Complete-download SHA-256 promotion
13. Proxy connectivity/reconnect smoke test
14. Large-file behavior above Telegram per-file limits
15. Telegram Topic recognition + Topic → Category mapping
16. Batch Resource classification
```

Video is intentionally excluded.

## Recovery

To force a fresh Telegram login for one account:

```bash
docker compose stop telegram-drive
rm -f ./data/accounts/<account_name>.session
./login-account.sh <account_name> <phone>
docker compose up -d telegram-drive
```

Do not delete the PostgreSQL volume just to re-authenticate Telegram.
