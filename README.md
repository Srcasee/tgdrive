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

The scanner does **not** scan every Telegram dialog automatically. After the account is authorized, an administrator must explicitly configure each Telegram Source to scan.

Use the Web administrator interface/API in this order:

1. `GET /api/telegram/accounts` — find the account ID, for example `default` → account `1`.
2. `GET /api/telegram/accounts/<account_id>/dialogs` — discover dialogs for that authorized Telegram account.
3. Select the exact dialog by **numeric Telegram chat ID**. Do not identify a source by display name alone because names are not unique.
4. `POST /api/telegram/sources` — add the selected chat as an enabled scanning source.
5. Verify with PostgreSQL and scanner logs.

For a fresh deployment, the API sequence can be exercised with an authenticated Web-admin session. The following is the exact source payload used by the current real-device test:

```bash
# 1) discover dialogs for default account (account_id=1)
curl -sS \
  -b cookies.txt \
  http://127.0.0.1:8080/api/telegram/accounts/1/dialogs

# 2) configure the exact resource-bearing chat
curl -sS \
  -b cookies.txt \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8080/api/telegram/sources \
  -d '{"account_id":1,"telegram_chat_id":-1004413553797,"name":"My Documents"}'
```

The current real-device source is:

```text
account: default
account_id: 1
chat: My Documents
chat id: -1004413553797
```

Only explicitly configured sources are scanned. The scanner stores the physical Telegram identity as `(account_id, telegram_chat_id, message_id)` and also records `topic_id` when Telegram supplies topic metadata.

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
PUT /api/admin/resources/{resource_id}/categories
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
