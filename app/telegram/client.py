import asyncio
import os

from telethon import TelegramClient

from config import settings, validate_telegram_credentials
from plugins.runtime import PluginRuntime
from repositories.accounts import AccountRepository


clients = {}
account_repository = AccountRepository()
plugin_runtime = PluginRuntime()


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
    validate_telegram_credentials()
    sync_sessions()
    refresh_clients()
    return clients


def refresh_clients():
    """Reconcile runtime Telegram clients with enabled account records."""
    session_dir = settings.TG_SESSION_DIR
    enabled_accounts = account_repository.list_enabled_sessions()
    enabled_sessions = {row["session"] for row in enabled_accounts}

    for name in list(clients):
        if name in enabled_sessions:
            continue
        client = clients.pop(name)
        if client.is_connected():
            try:
                asyncio.get_running_loop().create_task(client.disconnect())
            except RuntimeError:
                pass
        print(f"[ACCOUNT] disabled runtime client: {name}", flush=True)

    if not os.path.exists(session_dir):
        return clients

    proxy_plugin = plugin_runtime.get_capability("telegram.proxy")
    for filename in os.listdir(session_dir):
        if not filename.endswith(".session"):
            continue
        name = filename[:-8]
        if name not in enabled_sessions:
            continue
        existing = clients.get(name)
        if existing is not None and existing.is_connected():
            continue
        if existing is not None:
            clients.pop(name, None)
        session = os.path.join(session_dir, name)
        proxy = proxy_plugin.get_proxy(name) if proxy_plugin else None
        clients[name] = TelegramClient(
            session,
            settings.TG_API_ID,
            settings.TG_API_HASH,
            proxy=proxy,
        )
    return clients


async def reconnect_clients():
    """Rebuild Telegram clients so current proxy/account settings take effect."""
    for name, client in list(clients.items()):
        if client.is_connected():
            await client.disconnect()
        clients.pop(name, None)
    plugin_runtime.refresh()
    refresh_clients()
    return clients


def get_client(account_id: int):
    session_name = account_repository.get_session(account_id)
    if not session_name:
        raise RuntimeError(f"Telegram account {account_id} not found or disabled")

    all_clients = get_clients()
    if session_name not in all_clients:
        raise RuntimeError(f"Session {session_name} not loaded")
    return all_clients[session_name]
