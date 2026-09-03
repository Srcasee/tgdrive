from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from telegram.client import reconnect_clients, refresh_clients
from telegram.runtime_events import notify_source_change

router = APIRouter()
account_repository = AccountRepository()


@router.get("/accounts")
def list_accounts(_: Principal = Depends(require_admin)):
    return account_repository.list_all()


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
