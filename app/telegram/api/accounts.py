from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from telegram.client import get_client

router = APIRouter()
account_repository = AccountRepository()


async def _account_view(account):
    item = dict(account)
    item["session_name"] = account.get("session")
    item["telegram_user_id"] = None
    item["telegram_username"] = account.get("username")
    item["telegram_phone"] = None
    item["server_address"] = None
    item["port"] = None

    if not account["enabled"]:
        return item

    try:
        client = get_client(account["id"])
        if not client.is_connected():
            await client.connect()
        me = await client.get_me()
        item["telegram_user_id"] = getattr(me, "id", None)
        item["telegram_username"] = getattr(me, "username", None) or account.get("username")
        item["telegram_phone"] = getattr(me, "phone", None)
        item["server_address"] = getattr(client.session, "server_address", None)
        item["port"] = getattr(client.session, "port", None)
    except Exception as exc:
        item["info_error"] = str(exc)
    return item


@router.get("/accounts")
async def list_accounts(_: Principal = Depends(require_admin)):
    return [await _account_view(account) for account in account_repository.list_all()]


@router.get("/accounts/{account_id}/info")
async def account_info(account_id: int, _: Principal = Depends(require_admin)):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    return await _account_view(account)


class AccountEnabledInput(BaseModel):
    enabled: bool


@router.put("/accounts/{account_id}/enabled")
async def set_account_enabled(
    account_id: int,
    data: AccountEnabledInput,
    request: Request,
    _: Principal = Depends(require_admin),
):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")

    lifecycle = getattr(request.app.state, "lifecycle", None)
    if lifecycle is None:
        raise HTTPException(status_code=503, detail="Telegram runtime is not initialized")

    try:
        lifecycle_result = await lifecycle.set_account_enabled(account_id, data.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"更新账号状态失败: {exc}") from exc

    updated = account_repository.get(account_id)
    result = await _account_view(updated)
    result["status"] = "ok"
    result["discovered"] = lifecycle_result.get("discovered", False)
    if lifecycle_result.get("discovery_error"):
        result["discovery_error"] = lifecycle_result["discovery_error"]
    return result
