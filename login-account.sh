#!/bin/sh
set -eu

ACCOUNT_NAME="${1:?用法: ./login-account.sh <account_name> <phone>}"
PHONE="${2:?用法: ./login-account.sh <account_name> <phone>}"

SESSION_DIR="${TG_SESSION_DIR:-/data/accounts}"
SESSION_PATH="${SESSION_DIR}/${ACCOUNT_NAME}"

COMPOSE="docker compose"
RUNTIME_SERVICE="telegram-drive"
DB_SERVICE="postgres"
RUNTIME_WAS_RUNNING=0

if ${COMPOSE} ps --status running --services 2>/dev/null | grep -qx "${RUNTIME_SERVICE}"; then
  RUNTIME_WAS_RUNNING=1
fi

restart_runtime() {
  if [ "${RUNTIME_WAS_RUNNING}" -eq 1 ]; then
    echo "[LOGIN] restarting Telegram runtime"
    ${COMPOSE} start "${RUNTIME_SERVICE}" >/dev/null
  fi
}

trap restart_runtime EXIT

echo "[LOGIN] account : ${ACCOUNT_NAME}"
echo "[LOGIN] session : ${SESSION_PATH}"
echo "[LOGIN] phone   : ${PHONE}"

# Telethon stores the session in SQLite. The long-running Telegram runtime may
# already have this session open, which can race with the interactive login and
# produce "sqlite3.OperationalError: database is locked". Pause that runtime
# while login.py owns the session file; it is restarted automatically afterwards.
if [ "${RUNTIME_WAS_RUNNING}" -eq 1 ]; then
  echo "[LOGIN] stopping Telegram runtime to avoid SQLite session lock"
  ${COMPOSE} stop "${RUNTIME_SERVICE}" >/dev/null
fi

${COMPOSE} up -d "${DB_SERVICE}" >/dev/null

echo "[DB] waiting for PostgreSQL to accept SQL queries"
DB_READY=0
i=0
while [ "$i" -lt 30 ]; do
  if ${COMPOSE} exec -T "${DB_SERVICE}" \
      psql -U tgdrive -d tgdrive -tAc 'SELECT 1' 2>/dev/null | grep -qx '1'; then
    DB_READY=1
    break
  fi
  i=$((i + 1))
  sleep 1
done

if [ "${DB_READY}" -ne 1 ]; then
  echo "[DB] PostgreSQL is not usable; refusing to start Telegram login" >&2
  echo "[DB] If this is a disposable test deployment, remove ./data/postgres and restart PostgreSQL" >&2
  exit 1
fi

echo "[DB] PostgreSQL database is ready"
echo "[LOGIN] starting Telegram login account=${ACCOUNT_NAME}"

${COMPOSE} run --rm \
  -e TG_PHONE="${PHONE}" \
  -e TG_SESSION_DIR="${SESSION_DIR}" \
  -e TG_ACCOUNT_NAME="${ACCOUNT_NAME}" \
  "${RUNTIME_SERVICE}" \
  python3 -m telegram.login
