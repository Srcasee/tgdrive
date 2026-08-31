from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.sources import SourceRepository
from telegram.client import get_client, reconnect_clients, refresh_clients


router = APIRouter(prefix="/api/telegram", tags=["telegram"])
account_repository = AccountRepository()
source_repository = SourceRepository()


@router.get("/accounts")
def list_accounts(_: Principal = Depends(require_admin)):
    return account_repository.list_all()


class AccountEnabledInput(BaseModel):
    enabled: bool


@router.put("/accounts/{account_id}/enabled")
async def set_account_enabled(
    account_id: int,
    data: AccountEnabledInput,
    _: Principal = Depends(require_admin),
):
    try:
        account_repository.set_enabled(account_id, data.enabled)
        refresh_clients()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "account_id": account_id, "enabled": data.enabled}


@router.post("/reconnect")
async def reconnect_telegram(_: Principal = Depends(require_admin)):
    clients = await reconnect_clients()
    return {"status": "ok", "accounts": sorted(clients)}


@router.get("/accounts/{account_id}/dialogs")
async def list_dialogs(account_id: int, _: Principal = Depends(require_admin)):
    try:
        client = get_client(account_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    connected_here = False
    if not client.is_connected():
        await client.connect()
        connected_here = True

    try:
        if not await client.is_user_authorized():
            raise HTTPException(status_code=401, detail="telegram session not authorized")
        return [
            {"id": dialog.id, "name": dialog.name}
            async for dialog in client.iter_dialogs(limit=200)
        ]
    finally:
        if connected_here:
            await client.disconnect()


class SourceCreate(BaseModel):
    account_id: int
    telegram_chat_id: int
    name: str


@router.post("/sources")
def add_source(data: SourceCreate, _: Principal = Depends(require_admin)):
    if not account_repository.exists(data.account_id):
        raise HTTPException(status_code=404, detail="account not found")
    try:
        source_repository.add(data.account_id, data.telegram_chat_id, data.name)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="source already exists or is invalid") from exc
    return {"status": "ok"}
