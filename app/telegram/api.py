from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from repositories.accounts import AccountRepository
from repositories.sources import SourceRepository
from telegram.client import get_client


router = APIRouter(prefix="/api/telegram", tags=["telegram"])
account_repository = AccountRepository()
source_repository = SourceRepository()


@router.get("/accounts")
def list_accounts():
    return account_repository.list_all()


@router.get("/accounts/{account_id}/dialogs")
async def list_dialogs(account_id: int):
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
def add_source(data: SourceCreate):
    source_repository.add(data.account_id, data.telegram_chat_id, data.name)
    return {"status": "ok"}
