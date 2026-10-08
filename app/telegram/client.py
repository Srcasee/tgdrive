import asyncio
import os
import re
import shutil
from pathlib import Path

from telethon import TelegramClient

from config import settings, validate_telegram_credentials
from plugins.runtime import PluginRuntime


clients = {}
plugin_runtime = PluginRuntime()

_LEGACY_ARCHIVED_SESSION_RE = re.compile(r"^(?P<name>.+)\.(?P<suffix>[0-9a-f]{32})\.session$")


def get_clients():
    validate_telegram_credentials()
    return clients


def refresh_clients(session_names):
    """Reconcile runtime Telegram clients with the supplied enabled sessions."""
    session_dir = settings.TG_SESSION_DIR
    enabled_sessions = set(session_names)

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


def archive_account_session(session_name):
    session_dir = Path(settings.TG_SESSION_DIR)
    session_file = session_dir / f"{session_name}.session"
    if not session_file.exists():
        return None
    archive_dir = session_dir / ".deleted"
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / f"{session_name}.session"
    shutil.move(str(session_file), str(target))
    return target


def list_archived_sessions():
    archive_dir = Path(settings.TG_SESSION_DIR) / ".deleted"
    if not archive_dir.exists():
        return []
    names = set()
    for path in archive_dir.glob("*.session"):
        match = _LEGACY_ARCHIVED_SESSION_RE.fullmatch(path.name)
        names.add(f"{match.group('name')}.session" if match else path.name)
    return sorted(names)


def _resolve_archived_session(archive_dir: Path, session_name: str):
    source = archive_dir / session_name
    if source.exists():
        return source
    login_name = session_name[:-8]
    candidates = []
    for path in archive_dir.glob(f"{login_name}.*.session"):
        match = _LEGACY_ARCHIVED_SESSION_RE.fullmatch(path.name)
        if match and match.group("name") == login_name:
            candidates.append(path)
    return candidates[0] if len(candidates) == 1 else None


def restore_account_session(session_name):
    if not session_name or Path(session_name).name != session_name or not session_name.endswith(".session"):
        raise ValueError("无效的 session 文件名")
    archive_dir = Path(settings.TG_SESSION_DIR) / ".deleted"
    source = _resolve_archived_session(archive_dir, session_name)
    if source is None:
        raise FileNotFoundError(f"归档 session 不存在: {session_name}")
    target = Path(settings.TG_SESSION_DIR) / session_name
    if target.exists():
        raise FileExistsError(f"活动 session 已存在: {session_name}")
    shutil.move(str(source), str(target))
    return target


async def disconnect_account_session(session_name):
    client = clients.pop(session_name, None)
    if client is not None and client.is_connected():
        await client.disconnect()


async def reconnect_clients(session_names):
    """Rebuild Telegram clients for the supplied enabled sessions."""
    for name, client in list(clients.items()):
        if client.is_connected():
            await client.disconnect()
        clients.pop(name, None)
    plugin_runtime.refresh()
    return refresh_clients(session_names)


def get_client(session_name):
    if not session_name:
        raise RuntimeError("Telegram session is required")
    all_clients = refresh_clients([session_name])
    if session_name not in all_clients:
        raise RuntimeError(f"Session {session_name} not loaded")
    return all_clients[session_name]
