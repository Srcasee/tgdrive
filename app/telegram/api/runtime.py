from fastapi import APIRouter, Depends

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from telegram import client as telegram_client
from telegram.runtime_events import notify_dialog_refresh

router = APIRouter()
account_repository = AccountRepository()


@router.post("/reconnect")
async def reconnect_telegram(_: Principal = Depends(require_admin)):
    enabled = account_repository.list_enabled_sessions()
    clients = await telegram_client.reconnect_clients(row["session"] for row in enabled)
    notify_dialog_refresh()
    return {"status": "ok", "accounts": sorted(clients)}


@router.post("/reconcile")
async def reconcile_telegram(_: Principal = Depends(require_admin)):
    notify_dialog_refresh()
    return {"status": "accepted"}
