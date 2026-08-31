#!/bin/sh
set -eu

# One-command bootstrap for a fresh Docker host.
# Existing .env is preserved; set environment variables for non-interactive use.

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

command -v docker >/dev/null 2>&1 || { echo "[DEPLOY] docker is required" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "[DEPLOY] docker compose plugin is required" >&2; exit 1; }

mkdir -p data/accounts data/postgres

if [ ! -f .env ]; then
    API_ID=${TG_API_ID:-}
    API_HASH=${TG_API_HASH:-}
    PHONE=${TG_PHONE:-}
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
    if [ -z "$PHONE" ]; then
        printf "TG_PHONE: "
        read -r PHONE
    fi
    if [ -z "$ADMIN_PASS" ]; then
        printf "ADMIN_PASSWORD: "
        stty -echo
        read -r ADMIN_PASS
        stty echo
        printf "\n"
    fi

    if [ -z "$API_ID" ] || [ -z "$API_HASH" ] || [ -z "$PHONE" ] || [ -z "$ADMIN_PASS" ]; then
        echo "[DEPLOY] Telegram API credentials, phone and admin password are required" >&2
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
TG_PHONE=$PHONE
TG_SESSION_DIR=/data/accounts
TG_CONNECT_TIMEOUT=60
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
    echo "[DEPLOY] created .env"
else
    echo "[DEPLOY] using existing .env"
fi

echo "[DEPLOY] validating Compose configuration"
docker compose config >/dev/null

echo "[DEPLOY] building and starting Core + PostgreSQL"
docker compose up -d --build

echo "[DEPLOY] waiting for services"
sleep 5
docker compose ps

echo "[DEPLOY] bootstrap complete"
echo "[DEPLOY] next: ./login-account.sh <account_name> <phone>"
echo "[DEPLOY] then configure a Telegram source from the authenticated admin UI/API"
