from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from telegram.client import get_client, refresh_clients
from telegram.runtime_events import notify_source_change

router = APIRouter()
account_repository = AccountRepository()


@router.get("/accounts")
def list_accounts(_: Principal = Depends(require_admin)):
    return account_repository.list_all()


@router.get("/accounts/{account_id}/info")
async def account_info(account_id: int, _: Principal = Depends(require_admin)):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    try:
        client = get_client(account_id)
        if not client.is_connected():
            await client.connect()
        me = await client.get_me()
        status = getattr(me, "status", None)
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
                "first_name": getattr(me, "first_name", None),
                "last_name": getattr(me, "last_name", None),
                "username": getattr(me, "username", None),
                "phone": getattr(me, "phone", None),
                "bot": getattr(me, "bot", None),
                "verified": getattr(me, "verified", None),
                "premium": getattr(me, "premium", None),
                "restricted": getattr(me, "restricted", None),
                "scam": getattr(me, "scam", None),
                "fake": getattr(me, "fake", None),
                "support": getattr(me, "support", None),
                "lang_code": getattr(me, "lang_code", None),
                "status": type(status).__name__ if status is not None else None,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"无法读取 Telegram 账号信息: {exc}") from exc


class AccountEnabledInput(BaseModel):
    enabled: bool


@router.put("/accounts/{account_id}/enabled")
async def set_account_enabled(account_id: int, data: AccountEnabledInput, _: Principal = Depends(require_admin)):
    try:
        account_repository.set_enabled(account_id, data.enabled)
        refresh_clients()
        notify_source_change()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "account_id": account_id, "enabled": data.enabled}
