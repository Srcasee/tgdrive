from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.runtime_events import notify_dialog_refresh, notify_source_change

router = APIRouter()
account_repository = AccountRepository()
dialog_repository = DialogRepository()
source_repository = SourceRepository()


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


class DialogEnabledInput(BaseModel):
    enabled: bool


@router.put("/accounts/{account_id}/dialogs/{telegram_chat_id}/enabled")
async def set_dialog_enabled(
    account_id: int,
    telegram_chat_id: int,
    data: DialogEnabledInput,
    _: Principal = Depends(require_admin),
):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    if not account["enabled"]:
        raise HTTPException(status_code=409, detail="account disabled")

    dialog = dialog_repository.get_for_account(account_id, telegram_chat_id)
    if not dialog or dialog["entity_type"] != "Channel" or not dialog["is_channel"]:
        raise HTTPException(status_code=404, detail="channel not found")

    if data.enabled:
        source = source_repository.ensure_enabled(account_id, telegram_chat_id, dialog["name"] or str(telegram_chat_id))
    else:
        source = source_repository.get_for_chat(account_id, telegram_chat_id)
        if source is not None:
            source = source_repository.set_enabled(source["id"], False)
        else:
            source = {"account_id": account_id, "telegram_chat_id": telegram_chat_id, "enabled": False}

    notify_source_change()
    return {"status": "ok", "account_id": account_id, "telegram_chat_id": telegram_chat_id, "enabled": source["enabled"]}


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
