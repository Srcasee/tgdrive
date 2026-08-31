#!/bin/sh
set -eu

ACCOUNT_NAME="${1:?用法: ./login-account.sh <account_name> <phone>}"
PHONE="${2:?用法: ./login-account.sh <account_name> <phone>}"

SESSION_DIR="${TG_SESSION_DIR:-/data/accounts}"
SESSION_PATH="${SESSION_DIR}/${ACCOUNT_NAME}"

echo "[LOGIN] account : ${ACCOUNT_NAME}"
echo "[LOGIN] session : ${SESSION_PATH}"
echo "[LOGIN] phone   : ${PHONE}"

docker compose run --rm \
  -e TG_PHONE="${PHONE}" \
  -e TG_SESSION_DIR="${SESSION_DIR}" \
  -e TG_ACCOUNT_NAME="${ACCOUNT_NAME}" \
  telegram-drive \
  python3 -m telegram.login
