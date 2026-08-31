# Deployment Notes

## Deployment contract

The supported deployment is deliberately small:

```text
./deploy.sh
  |
  +--> persistent ./data/accounts
  +--> persistent ./data/postgres
  +--> .env generation/validation
  |
  v
docker compose up -d --build
  |
  +--> PostgreSQL
  +--> tgdrive Core

Optional only when required by the server/network:
  docker compose --profile proxy up -d --build
```

The Core image contains the application code. Runtime data is persisted under `./data`. The normal service mounts the optional Proxy plugin; the Video plugin is not part of the Core runtime.

## Fresh-server bootstrap

The preferred path is:

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
./deploy.sh
```

If `.env` is absent, the script prompts for Telegram API ID/hash, Telegram phone and Web admin password, generates `AUTH_SECRET` and a safe PostgreSQL password, writes `.env` with mode `600`, validates Compose, builds the Core image and starts the stack.

For unattended use, set `TG_API_ID`, `TG_API_HASH`, `TG_PHONE` and `ADMIN_PASSWORD` in the environment before invoking `./deploy.sh`. An existing `.env` is preserved.

The bootstrap intentionally stops before Telegram account authorization and source selection. Those operations require an operator to complete Telegram OTP/2FA and explicitly choose the Telegram chat to index.

## Normal post-bootstrap procedure

1. Verify services:

```bash
docker compose ps
docker compose logs --tail=100 telegram-drive
```

2. Authorize an account:

```bash
./login-account.sh default +1234567890
```

3. Open the Web UI on port `8080`.
4. Discover dialogs through the authenticated Telegram management surface.
5. Configure the exact Telegram chat/source by numeric chat ID.
6. Verify scanner logs and Resource catalog.

No manual PostgreSQL SQL or manual account-row creation is required for normal bootstrap.

## Data and storage rules

- PostgreSQL stores metadata, Resource identity, categories, source state and account metadata.
- Telegram remains the source of file bytes.
- Scanner/Ingestion is metadata-only and must not download a complete file merely to index it.
- Telegram session files are persisted under `/data/accounts/<account_name>` by default.
- The physical `files` table represents Telegram-backed locations; it is not a public File API.
- Physical Telegram identity is `(account_id, telegram_chat_id, message_id)`.
- `topic_id` is already persisted for Telegram messages but Topic-based automatic classification is not yet implemented.

## Web UI

The active UI is a dependency-free Resource-first browser client. It uses `/catalog`, `/catalog/search`, `/resources/{id}/download`, `/resources/{id}/share`, and Resource-level admin classification endpoints.

There are no compatibility `/files/*` HTTP routes.

Current real-device UI verification: login, catalog, search, category filtering, category create/delete, share-link lifecycle and basic download all work. Batch Resource classification remains pending.

## Proxy deployment

Proxy is an external plugin under `plugins/proxy/` and is not a Core storage/domain dependency.

Default:

```env
TG_PROXY_ENABLED=false
```

Proxy-enabled deployment:

```env
TG_PROXY_ENABLED=true
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
```

Then:

```bash
docker compose --profile proxy up -d --build
```

Core does not perform country/region detection and does not contain concrete proxy protocol logic.

Changing proxy configuration requires Telegram client recreation. The administrator `/api/telegram/reconnect` endpoint now performs that rebuild; a full application restart is also sufficient.

## CI deployment gate

GitHub Actions validates:

- full PostgreSQL test suite on Python 3.11 and 3.12;
- shell syntax of `deploy.sh` and `login-account.sh`;
- Docker Compose configuration parsing;
- Core Docker image build;
- Proxy plugin Docker image build.

## Current real-device verification

Verified on the current deployment:

```text
Core + PostgreSQL health                    PASS
Telegram login/session reuse               PASS
Multiple account sessions                   PASS
Explicit Telegram source configuration      PASS
Metadata-only incremental scan              PASS
Resource catalog/search                     PASS
Category create/delete/filter               PASS
Share link generate/display/delete/download PASS
Basic Resource download                     PASS
```

Observed and pending:

```text
Download throughput                         TOO SLOW
Telegram → VPS benchmark                    PENDING
FastAPI → VPS benchmark                     PENDING
Browser → VPS benchmark                     PENDING
Multi-account failover                      PENDING
HTTP Range real-file test                   PENDING
SHA-256 canonical promotion                 PENDING
Proxy smoke/throughput                      PENDING
Large-file >2 GiB/4 GiB validation          PENDING
Telegram Topic automation                   NOT IMPLEMENTED
Batch Resource classification                NOT IMPLEMENTED
```

A tested ~276 MB MP4 is stored as `files.id=9`, `resource_id=12`, `telegram_chat_id=-1004413553797`, `message_id=9`, `account_id=1`. It is the preferred repeatable benchmark fixture.

## Known engineering gaps

- Issue #21: measurement-driven Delivery transport optimization.
- Issue #19: richer Resource source health/ranking/retry policy.
- Issue #18: complete Telegram account lifecycle/health administration.
- Issue #15: further Scanner/Ingestion orchestration refinement.
- Issue #22: internal top-level `telegram` namespace cleanup.

Planned product issues cover Telegram Topic → Category mapping and batch Resource classification.

## Video

Video playback/chunk caching is outside the current real-device test plan. The optional plugin is not loaded by the normal Core runtime and must remain independent of cataloging, scanning, Resource identity and ordinary download delivery.
