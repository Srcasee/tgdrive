# Deployment Notes

## Current real deployment status

The staged Debian 12 deployment has reached a healthy Telegram-backed Core runtime:

- PostgreSQL 16 container: healthy.
- Core container: running and serving port 8000 internally / 8080 on the host.
- `default.session` is reused from the account session directory.
- Telegram account `default` is authorized.
- Telegram dialogs are available through the API.
- Sources are explicitly selected by `account_id` + `telegram_chat_id`.
- The validated source scanner indexed 9 files successfully.
- Complete JPG download works.
- MP4 Range streaming returns HTTP 206 with correct `Content-Range` semantics.
- SOCKS5 connectivity through the built-in proxy runtime has been validated.

## Simplified deployment contract

Normal deployment should require only:

1. Copy `.env.example` to `.env` and fill Telegram credentials plus `AUTH_SECRET`.
2. `docker compose up -d --build`.
3. Run `docker compose exec telegram-drive python -m telegram.login` once for a new account.
4. Select the exact Telegram chat in the UI and add it as a source.

Session discovery automatically creates the account database row. Manual SQL and manual account registration are not required for the normal single-account path.

## Proxy architecture

Proxy handling is now unified under `app/plugins/proxy`.

- Direct connectivity is the default.
- SOCKS5 is selected with `TG_PROXY_ENABLED=true` and `TG_PROXY_PLUGIN=socks5`.
- Login and runtime Telegram clients resolve proxy configuration through the same `ProxyRuntime`.
- Legacy `ENABLE_PROXY`, `PROXY_HOST`, `PROXY_PORT`, and `PROXY_TYPE` settings are removed from the supported configuration.
- The old external `plugins/tgdrive-proxy-socks5` package and `ProxyManager` compatibility facade are removed.

## Resolved documentation issues

### FastAPI lifecycle deprecation — resolved

Core now uses FastAPI's lifespan context instead of deprecated `on_event()` startup/shutdown handlers.

### Python version coverage — resolved

CI now tests both Python 3.11 and 3.12, matching the supported deployment range currently exercised by the project.

### Telegram package namespace — tracked separately

Issue #12 remains open because renaming the internal top-level `telegram` package is a broader compatibility refactor. The current test workaround is not being represented as a completed architectural fix.

## Performance status

Download optimization is intentionally paused after the first real-server benchmark. The baseline is preserved in `docs/PHASE-2-DOWNLOAD.md` and Issue #13. Browser/video-player simulation remains the final validation step after transport work resumes.
