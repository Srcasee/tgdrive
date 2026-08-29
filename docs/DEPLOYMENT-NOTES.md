# Deployment Notes

## Current real deployment status

The staged deployment on a Debian 12 server has reached a healthy real Telegram integration baseline:

- PostgreSQL 16 container: healthy.
- Database schema initialization: successful.
- Core container: running and serving port 8000 internally / 8080 on the host.
- Telegram session file `default.session` is present and the account is authorized.
- Telegram dialog discovery succeeds through `/api/telegram/accounts/1/dialogs`.
- A configured source (`telegram_chat_id=-1004413553797`) was scanned successfully.
- The source scan indexed 9 files and reports `scan_status=success`.
- JPG download returns HTTP 200 and a valid image.
- MP4 Range streaming returns HTTP 206 with correct byte ranges.
- SOCKS5 TCP/TLS connectivity was validated from the Core container.
- Telethon successfully connects and authorizes through the configured proxy.

## Download performance status

The HTTP transport is functionally working, but download-speed optimization is not complete.

Real-server benchmark against a 276,027,608-byte MP4:

- 1 MiB first range: 6.60 s / 0.16 MB/s.
- 8 MiB first range: 4.23 s / 1.98 MB/s.
- 8 MiB middle range: 149.57 s / 0.056 MB/s.
- Five repeated 8 MiB ranges: 0.77–0.91 MB/s.

This variability is now the Phase 2 baseline. Do not interpret it as proof that Telegram itself is imposing a fixed limit. The next step is controlled direct-vs-proxy and offset/cold-cache profiling before changing concurrency or transport architecture.

Real video-player simulation is intentionally deferred until the final Phase 2 validation stage.

## Migration / staged rollout checklist

1. Validate host/runtime compatibility without replacing the system Python.
2. Start PostgreSQL and verify schema initialization.
3. Start Core and verify HTTP health.
4. Configure authentication secrets through deployment environment only.
5. Enable proxy runtime only after independent proxy connectivity is verified.
6. Verify Telegram account authorization and dialog discovery.
7. Add only the intended Telegram source by its exact chat ID.
8. Run an incremental scan and verify PostgreSQL `telegram_sources.scan_status=success`.
9. Verify indexed file count and metadata.
10. Verify one complete file download.
11. Verify one MP4 HTTP Range request.
12. Run the Phase 2 throughput benchmark matrix.
13. Optimize transport only after the baseline is recorded.
14. Run realistic browser/video-player simulation last.

## Source selection warning

Telegram dialog names are not unique. Two dialogs may have the same display name but different Telegram chat IDs. Source configuration must therefore use the exact `telegram_chat_id`, not a name-only match. The scanner only scans sources explicitly present in `telegram_sources`; dialog discovery itself does not mean every dialog is being indexed.

## Known non-blocking issues

### FastAPI lifecycle deprecation

`app/core/app.py` still uses FastAPI `on_event()` startup/shutdown handlers. FastAPI reports these APIs as deprecated and recommends lifespan event handlers. This currently does not block startup or tests, but should be migrated during a later Core cleanup for forward compatibility.

### PostgreSQL connection messages

The deployment log can contain repeated `Server closed the connection: 0 bytes read on a total of 8 expected bytes` messages. The Core remains healthy and scans continue successfully, so this is currently tracked as an infrastructure/connection-pool investigation rather than a Telegram authorization failure.

### Python version coverage

The PostgreSQL CI workflow currently tests Python 3.12, while the current real deployment server uses Python 3.11.2. TGDrive is intended to select a compatible Python runtime from the deployment server rather than bind deployment to one Python version. The server has successfully installed the current dependencies under Python 3.11.2, but CI does not yet test a Python 3.11 matrix. Future CI work should define and test the supported Python range explicitly.

## Deployment-specific notes

### AUTH_SECRET is an intentional deployment secret

`AUTH_SECRET` must be supplied by the deployment operator through the environment. It is intentionally not committed to the repository and must never be generated as a fixed repository default. A deployment should generate a cryptographically random value and store it in the server's `.env` or secret-management system.

The application correctly fails startup when `AUTH_SECRET` is absent because authentication token signing cannot be safely initialized without it.

### Compose database hostname is container-scoped

The default Compose `DATABASE_URL` uses `postgres:5432`. `postgres` is the PostgreSQL service name on the Docker Compose network and is resolvable from application containers, but not from Python processes executed directly on the host.

Therefore:

- Core/database commands executed inside `telegram-drive` should use the Compose URL with host `postgres`.
- Host-side Python commands must not assume that `postgres` is resolvable.
- Do not expose PostgreSQL publicly or change the application URL merely to make host-side commands work.

### Host Python and container Python are different runtimes

The current test server has Python 3.11.2 on the host, while the current Docker image uses Python 3.12. This is acceptable for the present staged deployment test. The longer-term deployment tooling requirement remains that deployment should detect the server's available Python runtime and create a compatible environment rather than hard-code Python 3.12.

## CI verification

Run #78 (`8f2bf4f`) passed with 35 tests. The previous PostgreSQL `filename NOT NULL` error was addressed by explicit repository validation and regression coverage.

## Staged deployment principle

Database initialization, Core startup, optional proxy runtime, Telegram runtime, scanning, and real download performance testing are verified independently so a failure does not require restarting the entire deployment process.
