# tgdrive

Telegram-backed personal file drive with HTTP Range streaming.

## Quick start

1. Copy `.env.example` to `.env` and set `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`, and a strong `AUTH_SECRET`.
2. Start the stack with Docker Compose.
3. Run the one-time Telegram login command from the Core container. If a session already exists, login is skipped by Telethon.
4. Open the web UI, sign in, select the exact Telegram dialog/chat, and add it as a source.
5. Wait for the scanner; files then appear in the drive.

The deployment should not require manual PostgreSQL SQL, manual account-row creation, or hand-written proxy configuration for the normal single-account case.

## Telegram login

```bash
docker compose exec telegram-drive python -m telegram.login
```

The login command and runtime use the same proxy runtime. No separate legacy login proxy settings are used.

## Proxy

Proxy support is built into `app/plugins/proxy`. The default is direct connectivity. To enable SOCKS5:

```text
TG_PROXY_ENABLED=true
TG_PROXY_PLUGIN=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
```

Optional username/password are supported with `TG_PROXY_USERNAME` and `TG_PROXY_PASSWORD`.

## Development

```bash
cp .env.example .env
# fill secrets and Telegram credentials

docker compose up -d --build
pytest -q
```

## Project status

- Phase 1 real Telegram integration: complete.
- Real-server Range/file transport validation: complete.
- Download-speed optimization: intentionally paused after baseline benchmarking.
- Browser/video-player simulation: final validation step, not yet the current focus.

See `docs/QUICKSTART.md`, `docs/MIGRATION.md`, `docs/DEPLOYMENT-NOTES.md`, and `docs/PHASE-2-DOWNLOAD.md` for operational details.
