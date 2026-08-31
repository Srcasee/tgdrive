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

`deploy.sh` performs only the base infrastructure bootstrap: checks Docker, creates persistent directories, creates `.env` when needed, generates deployment secrets, validates Compose, builds Core and starts PostgreSQL + tgdrive. It does **not** log in a Telegram account and does **not** enable or configure the optional proxy. Existing `.env` files are preserved.

### Deployment order

Follow this order on a new server:

```text
1. ./deploy.sh
       │
       ├─ creates/validates .env
       ├─ starts PostgreSQL + Core
       └─ prints the next manual configuration steps

2. Configure Telegram account(s)
       │
       └─ ./login-account.sh <account_name> <phone>

3. Configure Telegram source(s)
       │
       └─ Web administrator discovers dialogs and selects exact chat IDs

4. Optional: configure Proxy
       │
       ├─ edit .env with TG_PROXY_* values
       ├─ set TG_PROXY_ENABLED=true
       └─ docker compose --profile proxy up -d --build

5. Verify
       │
       ├─ docker compose ps
       └─ docker compose logs --tail=100 telegram-drive
```

**Proxy can be configured either before or after `deploy.sh`, but the recommended and supported procedure is after `deploy.sh`.** The reason is that `deploy.sh` creates the initial `.env` when it does not exist. If proxy settings are prepared beforehand, they should be supplied through an existing `.env` so `deploy.sh` preserves them; otherwise configure them after the bootstrap. Never put real proxy credentials into the repository or `.env.example`.

Then authorize an account explicitly:

```bash
./login-account.sh default +1234567890
```

Open `http://<server>:8080/`, log in with the configured Web administrator, discover the Telegram dialogs and configure the exact Telegram chat/source to scan.

`login-account.sh` is only a deployment wrapper around the canonical `app/telegram/login.py` implementation. Account-named sessions are stored under `/data/accounts/<account_name>`. Multiple Telegram accounts/sessions are supported.

Scanning is metadata-only: a large Telegram file is not downloaded to the server merely because it is indexed.

See `docs/QUICKSTART.md`, `docs/DEPLOYMENT-NOTES.md`, and `docs/PROJECT-STATUS.md` for the operator procedure and current real-device status.

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

Recommended procedure after the base deployment:

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

GitHub Actions runs the PostgreSQL integration suite on Python 3.11 and 3.12 and validates the deployment scripts, Compose model, Core image and proxy image build.

## Current real-device status

Verified on the current real server:

- Telegram account login/session reuse: PASS (`default` and `Asada`).
- Explicit Telegram source configuration and incremental scanning: PASS.
- Resource catalog/search/category filtering: PASS.
- Category create/delete: PASS.
- Share-link creation, visible link, deletion and shared download: PASS.
- Basic Resource download: PASS.

Known pending work:

- Download performance is currently unacceptable (roughly 100 KB/s observed on the tested deployment); benchmark-driven transport optimization is next.
- Multi-account failover, Range, complete-download SHA-256 promotion and proxy smoke tests need explicit real-device validation.
- Telegram supergroup Topic recognition and automatic Topic → Category mapping are planned.
- Batch Resource classification is planned.

See `docs/ARCHITECTURE.md` for the target architecture and `docs/PROJECT-STATUS.md` for the detailed implementation/real-device matrix.
