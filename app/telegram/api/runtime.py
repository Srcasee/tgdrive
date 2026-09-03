from fastapi import APIRouter, Depends

from auth.dependencies import require_admin
from auth.models import Principal
from telegram.client import reconnect_clients
from telegram.runtime_events import notify_source_change

router = APIRouter()


@router.post("/reconnect")
async def reconnect_telegram(_: Principal = Depends(require_admin)):
    clients = await reconnect_clients()
    notify_source_change()
    return {"status": "ok", "accounts": sorted(clients)}


@router.post("/reconcile")
async def reconcile_telegram(_: Principal = Depends(require_admin)):
    notify_source_change()
    return {"status": "ok"}
