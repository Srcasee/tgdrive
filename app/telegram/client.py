import os

from telethon import TelegramClient

from config import settings
from plugins.proxy.runtime import ProxyRuntime
from repositories.accounts import AccountRepository


clients = {}
account_repository = AccountRepository()
proxy_runtime = ProxyRuntime()


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


def get_clients():
    if clients:
        return clients

    sync_sessions()
    session_dir = settings.TG_SESSION_DIR
    if not os.path.exists(session_dir):
        return clients

    for filename in os.listdir(session_dir):
        if not filename.endswith(".session"):
            continue
        name = filename[:-8]
        session = os.path.join(session_dir, name)
        proxy = proxy_runtime.resolve(name)
        clients[name] = TelegramClient(
            session,
            settings.TG_API_ID,
            settings.TG_API_HASH,
            proxy=proxy,
        )
    return clients


def get_client(account_id: int):
    session_name = account_repository.get_session(account_id)
    if not session_name:
        raise RuntimeError(f"Telegram account {account_id} not found")

    all_clients = get_clients()
    if session_name not in all_clients:
        raise RuntimeError(f"Session {session_name} not loaded")
    return all_clients[session_name]
