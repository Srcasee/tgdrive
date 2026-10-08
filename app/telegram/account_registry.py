import asyncio
import os

from repositories.accounts import AccountRepository
from telegram import client as telegram_client
from config import settings


account_repository = AccountRepository()
account_lock = asyncio.Lock()


def sync_sessions():
    session_dir = settings.TG_SESSION_DIR
    if not os.path.exists(session_dir):
        return

    for filename in os.listdir(session_dir):
        if not filename.endswith(".session"):
            continue
        session = filename[:-8]
        if account_repository.get_id_by_session(session) is None:
            account_repository.upsert_session(session)
            print("[ACCOUNT] auto added:", session, flush=True)


def enabled_sessions():
    sync_sessions()
    return account_repository.list_enabled_sessions()


def refresh_enabled_clients():
    rows = enabled_sessions()
    return telegram_client.refresh_clients(row["session"] for row in rows)


async def reconnect_enabled_clients():
    rows = enabled_sessions()
    return await telegram_client.reconnect_clients(row["session"] for row in rows)


def get_client(account_id):
    session_name = account_repository.get_session(account_id)
    if not session_name:
        raise RuntimeError(f"Telegram account {account_id} not found or disabled")
    return telegram_client.get_client(session_name)
