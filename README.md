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

Prerequisites: a Linux host with Docker Engine and the Docker Compose plugin, plus Telegram API credentials from `my.telegram.org`.

The supported fresh-server bootstrap is:

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
./deploy.sh
```

`deploy.sh` performs only the base infrastructure bootstrap: checks Docker, creates persistent directories, creates `.env` when needed, generates deployment secrets, validates Compose, builds Core and starts PostgreSQL + tgdrive. It does **not** log in a Telegram account and does **not** configure the optional proxy.

### Deployment order

The order below is mandatory when a Telegram proxy is required. **Configure and enable the proxy before the first Telegram login.** Do not wait for a failed Telegram login to discover that the proxy is needed.

```text
New server
   │
   ▼
./deploy.sh
   │
   ├── Docker 检查
   ├── 创建 data/
   ├── 创建 .env
   ├── Compose 校验
   ├── 构建 Core
   └── 启动 PostgreSQL + Core
   │
   ▼
如果需要 Proxy
   │
   ├── 编辑 .env
   ├── TG_PROXY_ENABLED=true
   ├── 配置 TG_PROXY_*
   └── docker compose --profile proxy up -d --build
   │
   ▼
Telegram 登录
./login-account.sh default <phone>
   │
   ▼
配置 Telegram Source
   │
   ▼
验证
```

`deploy.sh` creates the initial `.env` when it does not exist and preserves an existing `.env`. Therefore the normal procedure is: run `./deploy.sh` first, configure the proxy immediately afterward if required, then log in Telegram accounts. Never put real proxy credentials into the repository or `.env.example`.

### Telegram account login

Authorize an account explicitly:

```bash
./login-account.sh default +1234567890
```

A second account can use a different account name:

```bash
./login-account.sh Asada +861234567890
```

The resulting sessions are `/data/accounts/default.session` and `/data/accounts/Asada.session`. Account naming is intentional and the account name passed to `login-account.sh` is the session basename.

`login-account.sh` is only a deployment wrapper around the canonical `app/telegram/login.py` implementation. Account-named sessions are stored under `/data/accounts/<account_name>`. Multiple Telegram accounts/sessions are supported.

### Configure Telegram Source

After Telegram login, the authorized Telegram account can be queried for its dialogs. **This dialog discovery is not the same as enabling a source.** Only dialogs explicitly selected by an administrator become scanner sources.

The Source API requires the tgdrive Web-admin authentication cookie. A common mistake is to use `-b cookies.txt` before that file contains a valid `tgdrive_session`; that produces `401 authentication required`. First call `/auth/login` with `-c cookies.txt`, then reuse the cookie with `-b cookies.txt`.

Complete copy/paste flow for `default`:

```bash
# 0) Start from a clean cookie jar.
rm -f cookies.txt

# 1) Log in to the tgdrive Web API and save the admin session cookie.
#    Replace YOUR_ADMIN_PASSWORD with the value configured in .env.
curl -sS -c cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/auth/login \
  -d '{"username":"admin","password":"YOUR_ADMIN_PASSWORD"}'

# 2) Verify the Web-admin session.
curl -sS -b cookies.txt \
  http://127.0.0.1:8080/auth/me

# 3) List configured Telegram accounts and obtain the database account ID.
curl -sS -b cookies.txt \
  http://127.0.0.1:8080/api/telegram/accounts

# 4) List all Telegram dialogs for default (replace 1 if its account ID differs).
curl -sS -b cookies.txt \
  http://127.0.0.1:8080/api/telegram/accounts/1/dialogs

# 5) Add the selected Telegram chat as a scanner Source.
#    Replace the chat ID/name with the dialog selected in step 4.
curl -sS \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/api/telegram/sources \
  -d '{"account_id":1,"telegram_chat_id":-1004413553797,"name":"My Documents"}'

# 6) Verify the Source row.
docker compose exec postgres psql -U tgdrive -d tgdrive \
  -c 'SELECT id, account_id, telegram_chat_id, name, enabled, last_message_id FROM telegram_sources ORDER BY id;'

# 7) Watch the scanner.
docker compose logs --tail=200 telegram-drive | grep -E '\[SCAN\]|\[TG\]'
```

For another account, first get its `id` from `/api/telegram/accounts`, then use that ID in steps 4–5. The Telegram chat is identified by its **numeric `telegram_chat_id`**, not by display name alone.

The current real-device test uses:

```text
account: default
account_id: 1
chat: My Documents
chat id: -1004413553797
```

Only explicitly configured sources are scanned. The scanner stores the physical Telegram identity as `(account_id, telegram_chat_id, message_id)` and also records `topic_id` when Telegram supplies topic metadata.

### Automatic dialog discovery vs Source selection

A future improvement may automatically refresh/cache the complete Telegram dialog list after an account is authorized, so an administrator does not need to invoke the dialog endpoint manually. That does **not** require changing the target Resource architecture: dialog discovery is account metadata, while Source selection remains an explicit administrative control over what gets indexed.

Automatically scanning every dialog's messages/files would be a different behavior and is intentionally not part of the current architecture. It would remove the current Source allow-list boundary, increase Telegram API traffic and potentially ingest unintended chats. The preferred design is therefore: **automatic dialog discovery, manual Source selection, Source-scoped scanning**.

## Core API

The active HTTP API is Resource-first:

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

Categories are attached to logical Resources through the admin API:

```text
GET  /api/admin/categories
POST /api/admin/categories
PUT  /api/admin/categories/{category_id}
DELETE /api/admin/categories/{category_id}
PUT  /api/admin/resources/{resource_id}/categories
```

A batch Resource-classification API is planned; it is intentionally not represented as implemented until the backend and UI are complete.

Telegram account lifecycle is explicit:

```text
GET  /api/telegram/accounts
PUT  /api/telegram/accounts/{account_id}/enabled
POST /api/telegram/reconnect
GET  /api/telegram/accounts/{account_id}/dialogs
POST /api/telegram/sources
```

There are no compatibility `/files/*` HTTP endpoints. Physical Telegram locations are persistence details behind the Resource model.

A complete non-range delivery hashes the emitted content with SHA-256 and promotes the consumed physical location to its canonical Resource identity. Real-device verification of this promotion remains pending.

## Optional proxy

Direct Telegram connectivity is the default. Proxy is an external plugin and should only be enabled when the deployment/network requires it.

Configure it **before Telegram login**:

```bash
# edit .env first
# set TG_PROXY_ENABLED=true and configure TG_PROXY_*
docker compose --profile proxy up -d --build
```

The Core application does not contain country/region detection or concrete proxy protocol logic. Proxy configuration is deployment-controlled. After changing proxy settings, use the administrator reconnect endpoint or restart the service so Telegram clients are rebuilt.

## Resource model

The public domain model is Resource-first:

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

Physical Telegram identity is `(account_id, telegram_chat_id, message_id)`. The existing `topic_id` field is reserved for the planned Telegram Topic → Category mapping; it does not replace the physical identity.

## Video

Video chunk caching is intentionally outside the current Core delivery path and real-device test scope. The optional Video plugin is not a Core dependency and must not influence cataloging, scanning, Resource identity, or ordinary download delivery.

## Development and CI

```bash
cp .env.example .env
# fill required values

docker compose up -d --build
pytest -q
```

GitHub Actions defines the PostgreSQL integration workflow for Python 3.11 and 3.12, including the full test suite, deployment-script/Compose validation, Core image build and proxy image build. The latest main commit currently has **no reported GitHub Actions workflow run/status exposed through the repository integration**, so there is no CI error log to diagnose from that commit yet.

## Current real-device status

Verified on the current real server:

- Telegram account login/session reuse: PASS (`default` and `Asada`).
- Explicit Telegram source configuration and incremental scanning: PASS.
- Resource catalog/search/category filtering: PASS.
- Category create/delete: PASS.
- Share-link creation, visible link, deletion and shared download: PASS.
- Basic Resource download: PASS.
- Current test source `default / My Documents / -1004413553797` has produced indexed Resources.

Known pending work:

- Download performance is currently unacceptable (roughly 100 KB/s observed on the tested deployment); benchmark-driven transport optimization is next.
- Multi-account failover, Range, complete-download SHA-256 promotion and proxy smoke tests need explicit real-device validation.
- Telegram supergroup Topic recognition and automatic Topic → Category mapping are planned.
- Batch Resource classification is planned.
- Large-file behavior above Telegram per-file limits needs explicit real-device validation.

See `docs/ARCHITECTURE.md` for the target architecture and `docs/PROJECT-STATUS.md` for the detailed implementation/real-device matrix.
