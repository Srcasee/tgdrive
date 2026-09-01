from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.client import get_client, reconnect_clients, refresh_clients
from telegram.runtime_events import notify_source_change


router = APIRouter(prefix="/api/telegram", tags=["telegram"])
account_repository = AccountRepository()
dialog_repository = DialogRepository()
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
        notify_source_change()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "account_id": account_id, "enabled": data.enabled}


@router.post("/reconnect")
async def reconnect_telegram(_: Principal = Depends(require_admin)):
    clients = await reconnect_clients()
    notify_source_change()
    return {"status": "ok", "accounts": sorted(clients)}


@router.get("/accounts/{account_id}/dialogs")
async def list_dialogs(account_id: int, _: Principal = Depends(require_admin)):
    if not account_repository.exists(account_id):
        raise HTTPException(status_code=404, detail="account not found")
    return dialog_repository.list_for_account(account_id)


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
    notify_source_change()
    return {"status": "ok"}
