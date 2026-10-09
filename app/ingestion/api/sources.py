from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.runtime_events import notify_source_change

router = APIRouter()

account_repository = AccountRepository()
source_repository = SourceRepository()
dialog_repository = DialogRepository()


class SourceEnabledInput(BaseModel):
    enabled: bool


def _get_account_and_channel(account_id: int, telegram_chat_id: int):
    account = account_repository.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    if not account["enabled"]:
        raise HTTPException(status_code=409, detail="account disabled")

    dialog = dialog_repository.get_for_account(account_id, telegram_chat_id)
    if not dialog or dialog["entity_type"] != "Channel" or not dialog["is_channel"]:
        raise HTTPException(status_code=404, detail="channel not found")
    return dialog


@router.post("/sources/accounts/{account_id}/chats/{telegram_chat_id}")
def create_source(
    account_id: int,
    telegram_chat_id: int,
    _: Principal = Depends(require_admin),
):
    dialog = _get_account_and_channel(account_id, telegram_chat_id)
    existing = source_repository.get_for_chat(account_id, telegram_chat_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="source already exists")

    source_id = source_repository.add(
        account_id,
        telegram_chat_id,
        dialog["name"] or str(telegram_chat_id),
    )
    source = source_repository.get(source_id)
    notify_source_change()
    return {"status": "ok", "source": source}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, _: Principal = Depends(require_admin)):
    source = source_repository.delete(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    notify_source_change()
    return {"status": "ok", **source}


@router.put("/sources/accounts/{account_id}/chats/{telegram_chat_id}/enabled")
def set_dialog_source_enabled(
    account_id: int,
    telegram_chat_id: int,
    data: SourceEnabledInput,
    _: Principal = Depends(require_admin),
):
    _get_account_and_channel(account_id, telegram_chat_id)
    source = source_repository.get_for_chat(account_id, telegram_chat_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found; create it first")

    source = source_repository.set_enabled(source["id"], data.enabled)
    notify_source_change()
    return {"status": "ok", "source": source, "enabled": source["enabled"]}
