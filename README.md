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

For a completely new server, clone the repository and run the deployment script:

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
chmod +x deploy.sh
./deploy.sh
```

`deploy.sh` performs the base infrastructure bootstrap only: Docker checks, persistent directories, `.env`, secrets, Compose validation, Core build, and PostgreSQL + Core startup. It does **not** log in Telegram and does **not** enable the optional proxy.

### Fresh server deployment

The complete recommended flow is:

```text
New server
   ↓
git clone https://github.com/Srcasee/tgdrive.git
(git clone https://gh-proxy.com/https://github.com/Srcasee/tgdrive.git
git clone https://gh-proxy.com/https://github.com/Srcasee/tgdrive.git)

   ↓
cd tgdrive
   ↓
chmod +x deploy.sh
./deploy.sh
   ↓
PostgreSQL + Core healthy
   ↓
If Telegram needs proxy: enable TG_PROXY_ENABLED and TG_PROXY_* in .env
   ↓
docker compose --profile proxy up -d --build
   ↓
Telegram login
./login-account.sh <account-name> <phone>
   ↓
Core automatically refreshes Telegram dialogs
   ↓
Admin opens Web UI → Telegram → Dialogs
   ↓
Administrator enables a resource dialog
   ↓
Source is created/enabled and Scanner starts immediately
   ↓
Resources appear in the catalog / Source management
```

#### 1. Base deployment

Run `./deploy.sh` on a new Docker host. When `.env` does not exist, the script creates the required persistent directories, collects required credentials, generates deployment secrets, validates Compose, builds Core, initializes PostgreSQL and starts PostgreSQL + Core.

Verify:

```bash
docker compose ps
docker compose logs --tail=100 telegram-drive
```

The Core Web service is exposed on port `8080` by the default Compose configuration.

#### 2. Optional proxy

Direct Telegram connectivity is the default. **Proxy is optional and must be enabled explicitly by an administrator.** Configure it before Telegram login:

```bash
# Edit .env:
# TG_PROXY_ENABLED=true
# TG_PROXY_* = the required proxy settings

docker compose --profile proxy up -d --build
```

The fixed sing-box version required by the proxy is included in the repository, so the proxy image does not download sing-box during its build.

Verify:

```bash
docker compose --profile proxy ps
docker compose --profile proxy logs --tail=100 proxy
```

If proxy settings change later, use the administrator reconnect operation or restart Core so Telegram clients are rebuilt with the current connectivity configuration.

#### 3. Telegram login

After Core is healthy, log in each Telegram account explicitly:

```bash
./login-account.sh default +1234567890
./login-account.sh Asada +861234567890
```

Use a distinct account name for every session. The helper temporarily stops Core to avoid a SQLite session lock, performs the interactive login, then starts Core again.

After authorization, Core automatically reconciles the account and refreshes its Telegram dialog metadata. No extra command is required to trigger dialog discovery.

#### 4. Select a Telegram resource source

Open the Web UI at `http://<server-ip>:8080`, sign in as the administrator, then open **Telegram → Dialogs**.

Only selectable Telegram resource dialogs are presented. The current UI separates management into sidebar pages:

```text
Telegram
├── Dialogs
│   ├── Enable
│   ├── Disable
│   └── Delete
├── Source
└── Immediate reconciliation
```

Dialog semantics:

- **Enable** creates or re-enables the corresponding Telegram Source and immediately makes it eligible for Scanner processing.
- **Disable** disables the Source and removes that source's resources from the active catalog view.
- **Delete** removes the Dialog/Source management record, stops scanning, and removes its active resources from the catalog view.
- **Immediate reconciliation** forces Telegram dialog reconciliation without waiting for the normal periodic reconciliation interval.

The normal Telegram runtime reconciliation interval is one hour. Administrator actions that change Source state do not wait for that interval.

#### 5. Verify a fresh deployment

```bash
docker compose ps
curl -I http://127.0.0.1:8080
```

With proxy enabled:

```bash
docker compose --profile proxy ps
```

For a true zero-to-one deployment test, remove the old checkout and its test data/images as appropriate, clone the repository again, and run the sequence above. Do not rely on an existing Docker image, build cache, container, or persistent database when validating fresh-server behavior.

`deploy.sh` preserves an existing `.env`. Never put real proxy credentials or Telegram secrets into the repository or `.env.example`.

## Telegram Dialog discovery and Source selection

The Telegram flow has a strict security/data boundary:

```text
Telegram login
      ↓
Automatically iterate Telegram dialogs
      ↓
Persist/refresh selectable resource-dialog metadata only
      ↓
Administrator views Dialogs
      ↓
Administrator explicitly enables a target dialog
      ↓
Telegram Source
      ↓
Scanner
```

**Dialog discovery is metadata-only.** It reads Telegram dialog/entity information and does not download complete file payloads. Scanner processing starts only for enabled Sources.

For each authorized account, Core refreshes the cached dialog metadata during runtime reconciliation. The Web/API dialog view reads that cache; opening the view does not itself start a message scan.

A Telegram dialog is represented with its Telegram numeric chat ID and entity metadata. A value such as `id=-100...` is a Telegram supergroup/channel-style identifier; `type`, `group`, and `channel` describe the entity kind exposed by Telegram. These are Telegram identity/metadata fields, not Resource IDs.

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
GET  /api/telegram/sources
POST /api/telegram/sources
PUT  /api/telegram/sources/{source_id}/enabled
DELETE /api/telegram/sources/{source_id}
DELETE /api/telegram/accounts/{account_id}/dialogs/{telegram_chat_id}
```

The dialog endpoint is a cached metadata view. It does not imply Source creation or scanning.

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

Physical Telegram identity is `(account_id, telegram_chat_id, message_id)`. A logical Resource may have multiple Telegram-backed physical locations. `topic_id` is additional Telegram metadata and is reserved for Topic → Category mapping.

## Optional proxy

Direct Telegram connectivity is the default. Configure the optional proxy **before Telegram login**:

```bash
# edit .env: TG_PROXY_ENABLED=true and TG_PROXY_*
docker compose --profile proxy up -d --build
```

Core does not contain region detection or concrete proxy protocol logic. After proxy changes, use the administrator reconnect endpoint or restart Core.

## Video

Video chunk caching is outside the current Core delivery path. The optional Video plugin is not a Core dependency and must not influence cataloging, scanning, Resource identity, or ordinary download delivery.

## Development and CI

```bash
cp .env.example .env
# fill required values
docker compose up -d --build
pytest -q
```

GitHub Actions validates PostgreSQL integration, supported Python versions, the full test suite, deployment/Compose validation, Core image build and proxy image build. Recent feature work has focused on Telegram Source lifecycle and administrator management; download optimization is intentionally being treated as a separate measurement-driven phase.

## Current project status

### Verified on a real server

- Fresh-server bootstrap: **PASS**.
- Optional proxy deployment path: **PASS** in the previously validated deployment flow.
- Telegram account login/session reuse: **PASS**.
- Multiple account sessions: **PASS** (`default` and `Asada` were verified).
- Automatic dialog discovery/cache after account authorization: **PASS**.
- Resource-dialog filtering: **IMPLEMENTED**; only selectable resource groups/channels are persisted for admin selection.
- Source enable/disable/delete lifecycle: **IMPLEMENTED**.
- Scanner starts immediately for an enabled Source and remains idle when no Source is enabled: **PASS**.
- Periodic Telegram reconciliation plus administrator-triggered immediate reconciliation: **IMPLEMENTED**.
- Resource catalog/search/category filtering: **PASS**.
- Category create/delete: **PASS**.
- Share-link lifecycle and shared download: **PASS**.
- Basic Resource download: **FUNCTIONAL**, but throughput is currently too slow and is the next optimization target.

### Admin management status

The current Web UI uses a Telegram management sidebar with separate **Dialogs** and **Source** pages. Dialog state is Source-backed: enabling a Dialog creates/re-enables its Source; disabling it stops scanning and hides resources belonging only to that source; deleting it removes the management record and associated active catalog visibility. Reconciliation can be triggered immediately from the administrator UI.

### Pending

- Controlled download throughput benchmark and transport optimization (Issue #21).
- Multi-account download throughput/failover benchmark.
- Direct versus proxy throughput comparison where applicable.
- HTTP Range and repeated-range performance validation.
- Complete-download SHA-256 promotion validation on a large real file.
- Richer source health/ranking after measurements (Issue #19).
- Telegram Topic recognition and automatic Topic → Category mapping (Issue #29).
- Batch Resource classification (Issue #30).
- Telegram account health/retirement administration (Issue #18).
- Scanner/Ingestion orchestration refinement (Issue #15).
- Internal `telegram` package namespace cleanup (Issue #22).
- Large-file behavior above Telegram/account-specific limits.

See `docs/ARCHITECTURE.md` for the architectural invariants and `docs/PROJECT-STATUS.md` for the detailed implementation/real-device matrix.
