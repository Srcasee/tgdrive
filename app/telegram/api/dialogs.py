from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from telegram.runtime_events import notify_dialog_refresh

router = APIRouter()
account_repository = AccountRepository()
dialog_repository = DialogRepository()


@router.get("/dialogs")
async def list_all_dialogs(_: Principal = Depends(require_admin)):
    rows = dialog_repository.list_all()
    accounts = []
    account_map = {}

    for row in rows:
        account_id = row["account_id"]
        account = account_map.get(account_id)
        if account is None:
            account_row = account_repository.get(account_id)
            account = {
                "account_id": account_id,
                "nickname": account_row["name"] if account_row else None,
                "username": account_row["username"] if account_row else None,
                "channels": [],
            }
            account_map[account_id] = account
            accounts.append(account)

        account["channels"].append({
            "account_id": account_id,
            "telegram_chat_id": row["telegram_chat_id"],
            "name": row["name"],
            "username": row["username"],
            "entity_type": row["entity_type"],
            "is_group": row["is_group"],
            "is_channel": row["is_channel"],
            "updated_at": row["updated_at"],
            "source_enabled": row["source_enabled"],
            "source_id": row["source_id"],
            "scan_status": row["scan_status"],
        })

    return accounts


@router.post("/dialogs/refresh")
async def refresh_dialogs(_: Principal = Depends(require_admin)):
    notify_dialog_refresh()
    return {"status": "accepted"}


