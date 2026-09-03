import asyncio

from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.client import get_client
from telegram.dialog_discovery import DialogDiscoveryService

router = APIRouter()

account_repository = AccountRepository()
dialog_repository = DialogRepository()
source_repository = SourceRepository()
dialog_discovery = DialogDiscoveryService(dialog_repository, source_repository)
dialog_init_lock = asyncio.Lock()


@router.get("/accounts/{account_id}/dialogs")
async def list_dialogs(account_id: int, _: Principal = Depends(require_admin)):
    if not account_repository.exists(account_id):
        raise HTTPException(status_code=404, detail="account not found")

    dialogs = dialog_repository.list_for_account(account_id)
    if dialogs:
        return dialogs

    async with dialog_init_lock:
        dialogs = dialog_repository.list_for_account(account_id)
        if not dialogs:
            try:
                client = get_client(account_id)
                account = account_repository.get(account_id)
                account_name = account.get("session", str(account_id)) if account else str(account_id)
                await dialog_discovery.refresh(client, account_id, account_name)
            except Exception as exc:
                print(f"[TG] initial dialog discovery skipped: {exc}", flush=True)
        return dialog_repository.list_for_account(account_id)


@router.delete("/accounts/{account_id}/dialogs/{telegram_chat_id}")
async def delete_dialog(account_id: int, telegram_chat_id: int, _: Principal = Depends(require_admin)):
    if not account_repository.exists(account_id):
        raise HTTPException(status_code=404, detail="account not found")
    source = source_repository.get_for_chat(account_id, telegram_chat_id)
    if source is not None and source.get("enabled"):
        raise HTTPException(status_code=409, detail="disable source before deleting dialog")
    deleted = dialog_repository.delete(account_id, telegram_chat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="dialog not found")
    return {"status": "ok", "account_id": account_id, "telegram_chat_id": telegram_chat_id}
