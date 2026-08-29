# Deployment Notes

## Current real deployment status

The staged deployment on a Debian 12 server has reached a healthy Core runtime:

- PostgreSQL 16 container: healthy.
- Database schema initialization: successful.
- Core container: running and serving port 8000 internally / 8080 on the host.
- Core startup succeeds without Telegram credentials; the log reports that the Telegram runtime is disabled when Telegram is not configured.
- Telegram and proxy runtime testing remain separate stages and have not yet been enabled.

## Known non-blocking issues

### FastAPI lifecycle deprecation

`app/core/app.py` still uses FastAPI `on_event()` startup/shutdown handlers. FastAPI reports these APIs as deprecated and recommends lifespan event handlers. This currently does not block startup or tests, but should be migrated during a later Core cleanup for forward compatibility.

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

Schema initialization in the staged deployment is therefore performed from the Core container when using the Compose database URL.

### Host Python and container Python are different runtimes

The current test server has Python 3.11.2 on the host, while the current Docker image uses Python 3.12. This is acceptable for the present staged deployment test. The longer-term deployment tooling requirement remains that deployment should detect the server's available Python runtime and create a compatible environment rather than hard-code Python 3.12.

## CI verification

Run #78 (`8f2bf4f`) passed with 35 tests. The previous PostgreSQL `filename NOT NULL` error was addressed by explicit repository validation and regression coverage.

## Staged deployment principle

Database initialization, Core startup, optional proxy runtime, Telegram runtime, scanning, and real download performance testing are verified independently so a failure does not require restarting the entire deployment process.
