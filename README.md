# tgdrive

Telegram-only file catalog and delivery system.

```text
Telegram metadata
      ↓
Recognition / Ingestion
      ↓
Logical Resource
      ↓
Catalog / classification / search
      ↓
Resource delivery
      ↓
Telegram backing locations
```

Telegram is the only content backend. Multiple Telegram accounts are access/redundancy paths, not storage-provider backends.

## Quick start — fresh server

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
./deploy.sh
```

`deploy.sh` performs the base infrastructure bootstrap only: Docker checks, persistent directories, `.env`, secrets, Compose validation, Core build, and PostgreSQL + Core startup. It does **not** log in Telegram and does **not** configure the optional proxy.

### Deployment order

If a Telegram proxy is required, configure it **before the first Telegram login**:

```text
New server
   ↓
./deploy.sh
   ↓
If proxy is required: edit .env → TG_PROXY_ENABLED=true → configure TG_PROXY_* → docker compose --profile proxy up -d --build
   ↓
Telegram login
./login-account.sh default <phone>
   ↓
Automatic Telegram Dialog discovery/cache
   ↓
Administrator selects target dialog and creates Telegram Source
   ↓
Scanner scans Source only
   ↓
Verify
```

`deploy.sh` creates `.env` when absent and preserves an existing one. Never put real proxy credentials into the repository or `.env.example`.

## Telegram account login

```bash
./login-account.sh default +1234567890
./login-account.sh Asada +861234567890
```

The account name passed to `login-account.sh` is the session basename, e.g. `/data/accounts/default.session`. Multiple accounts/sessions are supported.

## Telegram Dialog discovery and Source selection

The Telegram flow has a strict security/data boundary:

```text
Telegram login
      ↓
Automatically iterate ALL Telegram dialogs
      ↓
Persist/refresh Dialog metadata only
      ↓
Administrator views dialogs
      ↓
Administrator explicitly selects a target group/channel
      ↓
POST /api/telegram/sources
      ↓
Scanner reads messages ONLY from enabled Sources
```

**Automatic Dialog discovery never scans message/file contents.** It only reads Telegram dialog metadata such as numeric chat ID, display name and entity type. An authorized Telegram account does not cause every conversation to be indexed.

After each authorized account connects, Core automatically refreshes its complete dialog metadata cache. The existing `/api/telegram/accounts/{account_id}/dialogs` endpoint then reads that cache; invoking it does not trigger a message scan. Source selection remains an explicit administrator action.

### Complete Source configuration command flow

The Source API requires the tgdrive Web-admin authentication cookie. First authenticate to tgdrive with `-c cookies.txt`; reusing an empty cookie jar with only `-b cookies.txt` returns `401 authentication required`.

```bash
# 0) Clean cookie jar.
rm -f cookies.txt

# 1) Log in to the tgdrive Web API. Replace YOUR_ADMIN_PASSWORD.
curl -sS -c cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/auth/login \
  -d '{"username":"admin","password":"YOUR_ADMIN_PASSWORD"}'

# 2) Verify Web-admin authentication.
curl -sS -b cookies.txt http://127.0.0.1:8080/auth/me

# 3) List Telegram accounts and find the account ID for default.
curl -sS -b cookies.txt http://127.0.0.1:8080/api/telegram/accounts

# 4) Read the automatically cached dialogs. Replace 1 if default has another ID.
curl -sS -b cookies.txt http://127.0.0.1:8080/api/telegram/accounts/1/dialogs

# 5) Select ONE target dialog by its numeric Telegram chat ID and create a Source.
curl -sS -b cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/api/telegram/sources \
  -d '{"account_id":1,"telegram_chat_id":-1004413553797,"name":"My Documents"}'

# 6) Verify configured Sources.
docker compose exec postgres psql -U tgdrive -d tgdrive \
  -c 'SELECT id, account_id, telegram_chat_id, name, enabled, last_message_id FROM telegram_sources ORDER BY id;'

# 7) Watch scanning. Only the selected Source should produce a [SCAN] dialog line.
docker compose logs --tail=200 telegram-drive | grep -E '\[SCAN\]|\[TG\]'
```

The current real-device test uses `default` account ID `1`, with `My Documents` chat ID `-1004413553797`. The important rule is: **Dialog discovery is automatic; Source selection is manual; file scanning is Source-scoped.**

The scanner's physical Telegram identity remains `(account_id, telegram_chat_id, message_id)` and `topic_id` is recorded when Telegram supplies topic metadata.

## Core API

```text
GET  /catalog
GET  /catalog/search?q=...
GET  /catalog/{resource_id}
GET  /resources/{resource_id}/download
HEAD /resources/{resource_id}/download
GET  /resources/{resource_id}/stream
HEAD /resources/{resource_id}/stream
POST /resources/{resource_id}/share
```

Categories:

```text
GET  /api/admin/categories
POST /api/admin/categories
PUT  /api/admin/categories/{category_id}
DELETE /api/admin/categories/{category_id}
PUT  /api/admin/resources/{resource_id}/categories
```

Telegram lifecycle:

```text
GET  /api/telegram/accounts
PUT  /api/telegram/accounts/{account_id}/enabled
POST /api/telegram/reconnect
GET  /api/telegram/accounts/{account_id}/dialogs
POST /api/telegram/sources
```

The dialog endpoint is a cached metadata view. It does not imply Source creation or scanning.

## Optional proxy

Direct Telegram connectivity is the default. Configure the optional proxy **before Telegram login**:

```bash
# edit .env: TG_PROXY_ENABLED=true and TG_PROXY_*
docker compose --profile proxy up -d --build
```

Core does not contain region detection or concrete proxy protocol logic. After proxy changes, use the administrator reconnect endpoint or restart Core.

## Resource model

```text
Telegram message
      │
      ├── account_id
      ├── telegram_chat_id
      ├── message_id
      └── topic_id (when Telegram provides a topic)
               │
               ▼
        physical `files` row
               │
          resource_id
               ▼
          logical Resource
               │
               ▼
        categories/search
```

Physical Telegram identity is `(account_id, telegram_chat_id, message_id)`. `topic_id` remains available for the planned Topic → Category mapping.

## Video

Video chunk caching is outside the current Core delivery path. The optional Video plugin is not a Core dependency and must not influence cataloging, scanning, Resource identity, or ordinary download delivery.

## Development and CI

```bash
cp .env.example .env
# fill required values
docker compose up -d --build
pytest -q
```

GitHub Actions covers PostgreSQL integration, Python 3.11/3.12, the full test suite, deployment/Compose validation, Core image build and proxy image build.

## Current real-device status

Verified:

- Telegram account login/session reuse: PASS (`default` and `Asada`).
- Automatic Telegram dialog discovery/cache: implemented; real-device restart verification pending.
- Explicit Telegram Source configuration and incremental scanning: PASS.
- Resource catalog/search/category filtering: PASS.
- Category create/delete: PASS.
- Share-link lifecycle and shared download: PASS.
- Basic Resource download: PASS.

Pending:

- Download performance benchmark and transport optimization (roughly 100 KB/s observed).
- Real-device verification that every authorized account refreshes its complete dialog cache without indexing messages.
- Multi-account failover, Range, complete-download SHA-256 promotion and proxy smoke tests.
- Telegram Topic recognition and automatic Topic → Category mapping.
- Batch Resource classification.
- Large-file behavior above Telegram per-file limits.

See `docs/ARCHITECTURE.md` for target architecture and `docs/PROJECT-STATUS.md` for the implementation/real-device matrix.
