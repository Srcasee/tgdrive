from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from catalog.repository import CatalogRepository
from telegram.client import get_client, refresh_clients
from telegram.dialog_discovery import DialogDiscoveryService
from telegram.runtime_events import notify_source_change

router = APIRouter()
account_repository = AccountRepository()
dialog_repository = DialogRepository()
source_repository = SourceRepository()
catalog_repository = CatalogRepository()
dialog_discovery = DialogDiscoveryService(dialog_repository, source_repository, catalog_repository)


@router.get("/accounts")
async def list_accounts(_: Principal = Depends(require_admin)):
    accounts = account_repository.list_all()
    result = []
    for account in accounts:
        item = dict(account)
        if not account["enabled"]:
            result.append(item)
            continue
        try:
            client = get_client(account["id"])
            if not client.is_connected():
                await client.connect()
            me = await client.get_me()
            item["telegram_user_id"] = getattr(me, "id", None)
            item["telegram_username"] = getattr(me, "username", None)
            item["telegram_phone"] = getattr(me, "phone", None)
            item["server_address"] = getattr(client.session, "server_address", None)
            item["port"] = getattr(client.session, "port", None)
            item["session_name"] = account.get("session")
        except Exception as exc:
            item["session_name"] = account.get("session")
            item["info_error"] = str(exc)
        result.append(item)
    return result


@router.get("/accounts/{account_id}/info")
async def account_info(account_id: int, _: Principal = Depends(require_admin)):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    if not account["enabled"]:
        return {
            "id": account["id"],
            "name": account.get("name"),
            "username": account.get("username"),
            "session_name": account.get("session"),
            "enabled": False,
            "connected": False,
            "server_address": None,
            "port": None,
            "telegram": {"id": None, "username": account.get("username"), "phone": None},
        }
    try:
        client = get_client(account_id)
        if not client.is_connected():
            await client.connect()
        me = await client.get_me()
        return {
            "id": account["id"],
            "name": account.get("name"),
            "username": account.get("username"),
            "session_name": account.get("session"),
            "enabled": account["enabled"],
            "connected": client.is_connected(),
            "dc_id": getattr(client.session, "dc_id", None),
            "server_address": getattr(client.session, "server_address", None),
            "port": getattr(client.session, "port", None),
            "telegram": {
                "id": getattr(me, "id", None),
                "username": getattr(me, "username", None),
                "phone": getattr(me, "phone", None),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"无法读取 Telegram 账号信息: {exc}") from exc


class AccountEnabledInput(BaseModel):
    enabled: bool


@router.put("/accounts/{account_id}/enabled")
async def set_account_enabled(account_id: int, data: AccountEnabledInput, _: Principal = Depends(require_admin)):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")

    if account["enabled"] == data.enabled:
        return {"status": "ok", "account_id": account_id, "enabled": data.enabled}

    if not data.enabled:
        sources = source_repository.list_enabled_for_account(account_id)
        chat_ids = [row["telegram_chat_id"] for row in sources]
        source_repository.disable_all_for_account(account_id)
        dialog_repository.delete_all_for_account(account_id)
        catalog_repository.deactivate_telegram_chats(account_id, chat_ids)

    account_repository.set_enabled(account_id, data.enabled)
    refresh_clients()
    notify_source_change()
    return {"status": "ok", "account_id": account_id, "enabled": data.enabled}
