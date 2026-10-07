from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from telegram.client import get_client, sync_sessions
from telegram.login_service import login_service


router = APIRouter()
account_repository = AccountRepository()


async def _account_view(account):
    item = dict(account)
    item["login_name"] = account.get("session")
    item["nickname"] = account.get("name") or account.get("username") or account.get("session")
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
        if not await client.is_user_authorized():
            item["authorized"] = False
            return item
        me = await client.get_me()
        nickname = " ".join(filter(None, [getattr(me, "first_name", None), getattr(me, "last_name", None)]))
        item["authorized"] = True
        item["nickname"] = nickname or account.get("username") or account.get("session")
        item["telegram_user_id"] = getattr(me, "id", None)
        item["telegram_username"] = getattr(me, "username", None) or account.get("username")
        item["telegram_phone"] = getattr(me, "phone", None)
        item["server_address"] = getattr(client.session, "server_address", None)
        item["port"] = getattr(client.session, "port", None)
    except Exception as exc:
        item["authorized"] = False
        item["info_error"] = str(exc)
    return item


@router.get("/accounts")
async def list_accounts(_: Principal = Depends(require_admin)):
    sync_sessions()
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


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: int,
    request: Request,
    _: Principal = Depends(require_admin),
):
    lifecycle = getattr(request.app.state, "lifecycle", None)
    if lifecycle is None:
        raise HTTPException(status_code=503, detail="Telegram runtime is not initialized")
    try:
        return await lifecycle.delete_account(account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除账号失败: {exc}") from exc


class LoginStartInput(BaseModel):
    login_name: str = Field(min_length=1, max_length=80)
    phone: str = Field(min_length=3, max_length=32)


class LoginCodeInput(BaseModel):
    login_id: str = Field(min_length=16, max_length=64)
    code: str = Field(min_length=1, max_length=32)


class LoginPasswordInput(BaseModel):
    login_id: str = Field(min_length=16, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginFlowInput(BaseModel):
    login_id: str = Field(min_length=16, max_length=64)


@router.post("/accounts/login/start")
async def start_account_login(data: LoginStartInput, _: Principal = Depends(require_admin)):
    try:
        return await login_service.start(data.login_name, data.phone)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"启动 Telegram 登录失败: {exc}") from exc


@router.get("/accounts/login/{login_id}")
async def account_login_status(login_id: str, _: Principal = Depends(require_admin)):
    try:
        return login_service.status(login_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/accounts/login/code")
async def submit_account_login_code(data: LoginCodeInput, _: Principal = Depends(require_admin)):
    try:
        return await login_service.submit_code(data.login_id, data.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"验证码验证失败: {exc}") from exc


@router.post("/accounts/login/password")
async def submit_account_login_password(data: LoginPasswordInput, _: Principal = Depends(require_admin)):
    try:
        return await login_service.submit_password(data.login_id, data.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"两步验证失败: {exc}") from exc


@router.post("/accounts/login/cancel")
async def cancel_account_login(data: LoginFlowInput, _: Principal = Depends(require_admin)):
    try:
        return await login_service.cancel(data.login_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
