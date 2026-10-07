from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository

router = APIRouter()
account_repository = AccountRepository()
dialog_repository = DialogRepository()
source_repository = SourceRepository()


@router.get("/accounts/{account_id}/dialogs")
async def list_dialogs(account_id: int, _: Principal = Depends(require_admin)):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    if not account["enabled"]:
        return []
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
