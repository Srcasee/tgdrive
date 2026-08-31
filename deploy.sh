#!/bin/sh
set -eu

# One-command bootstrap for a fresh Docker host.
# This script prepares the application and starts Core + PostgreSQL.
# Telegram accounts and proxy credentials are deliberately configured separately.
# Existing .env is preserved; set environment variables for non-interactive use.

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

echo "[DEPLOY] step 1/7: checking Docker prerequisites"
command -v docker >/dev/null 2>&1 || { echo "[DEPLOY] docker is required" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "[DEPLOY] docker compose plugin is required" >&2; exit 1; }

echo "[DEPLOY] step 2/7: preparing persistent directories"
mkdir -p data/accounts data/postgres

if [ ! -f .env ]; then
    echo "[DEPLOY] step 3/7: creating .env"
    API_ID=${TG_API_ID:-}
    API_HASH=${TG_API_HASH:-}
    ADMIN_USER=${ADMIN_USERNAME:-admin}
    ADMIN_PASS=${ADMIN_PASSWORD:-}

    if [ -z "$API_ID" ]; then
        printf "TG_API_ID: "
        read -r API_ID
    fi
    if [ -z "$API_HASH" ]; then
        printf "TG_API_HASH: "
        read -r API_HASH
    fi
    if [ -z "$ADMIN_PASS" ]; then
        printf "ADMIN_PASSWORD: "
        stty -echo
        read -r ADMIN_PASS
        stty echo
        printf "\n"
    fi

    if [ -z "$API_ID" ] || [ -z "$API_HASH" ] || [ -z "$ADMIN_PASS" ]; then
        echo "[DEPLOY] Telegram API credentials and admin password are required" >&2
        exit 1
    fi

    if command -v openssl >/dev/null 2>&1; then
        AUTH_SECRET=${AUTH_SECRET:-$(openssl rand -hex 32)}
        POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$(openssl rand -hex 24)}
    else
        echo "[DEPLOY] openssl is required to generate deployment secrets" >&2
        exit 1
    fi

    cat > .env <<EOF
TG_API_ID=$API_ID
TG_API_HASH=$API_HASH
# TG_PHONE is intentionally empty: accounts are added explicitly with login-account.sh.
TG_PHONE=
TG_SESSION_DIR=/data/accounts
TG_CONNECT_TIMEOUT=60

# Proxy is disabled until its server/credentials are configured below.
TG_PROXY_ENABLED=false
TG_PROXY_TYPE=socks5
TG_PROXY_HOST=proxy
TG_PROXY_PORT=1080
TG_PROXY_USERNAME=
TG_PROXY_PASSWORD=
SING_BOX_VERSION=1.13.19
SING_BOX_DOWNLOAD_BASE=https://github.com/SagerNet/sing-box/releases/download
TG_PROXY_UPSTREAM_TYPE=vless
TG_PROXY_VLESS_SERVER=
TG_PROXY_VLESS_PORT=443
TG_PROXY_VLESS_UUID=
TG_PROXY_VLESS_SERVER_NAME=
TG_PROXY_VLESS_WS_PATH=/
TG_PROXY_VLESS_WS_HOST=
TG_PROXY_RUNTIME_DIR=/tmp/tgdrive-proxy

POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql://tgdrive:$POSTGRES_PASSWORD@postgres:5432/tgdrive
AUTH_SECRET=$AUTH_SECRET
AUTH_COOKIE_SECURE=false
AUTH_TOKEN_TTL=86400
ADMIN_USERNAME=$ADMIN_USER
ADMIN_PASSWORD=$ADMIN_PASS
PORT=8000
EOF
    chmod 600 .env
    echo "[DEPLOY] .env created (Telegram phone/account and proxy were NOT configured)"
else
    echo "[DEPLOY] step 3/7: using existing .env"
fi

echo "[DEPLOY] step 4/7: validating Compose configuration"
docker compose config >/dev/null

echo "[DEPLOY] step 5/7: building Core + PostgreSQL"
docker compose build telegram-drive

echo "[DEPLOY] step 6/7: starting Core + PostgreSQL"
docker compose up -d postgres telegram-drive
sleep 5
docker compose ps

echo "[DEPLOY] step 7/7: bootstrap complete"
echo "[DEPLOY] Telegram account setup: ./login-account.sh <account_name> <phone>"
echo "[DEPLOY] Proxy setup: edit .env, set TG_PROXY_ENABLED=true and configure TG_PROXY_* values, then: docker compose --profile proxy up -d --build"
echo "[DEPLOY] Verify: docker compose logs --tail=100 telegram-drive"
