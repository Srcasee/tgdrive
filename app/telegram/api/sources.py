from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import require_admin
from auth.models import Principal
from repositories.accounts import AccountRepository
from repositories.sources import SourceRepository
from telegram.runtime_events import notify_source_change

router = APIRouter()

account_repository = AccountRepository()
source_repository = SourceRepository()


@router.get("/sources")
def list_sources(_: Principal = Depends(require_admin)):
    return source_repository.list_all_enabled()


class SourceCreate(BaseModel):
    account_id: int
    telegram_chat_id: int
    name: str


@router.post("/sources")
def add_source(data: SourceCreate, _: Principal = Depends(require_admin)):
    if not account_repository.exists(data.account_id):
        raise HTTPException(status_code=404, detail="account not found")
    try:
        source = source_repository.ensure_enabled(data.account_id, data.telegram_chat_id, data.name)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="source already exists or is invalid") from exc
    notify_source_change()
    return {"status": "ok", "source": source}


class SourceEnabledInput(BaseModel):
    enabled: bool


@router.put("/sources/{source_id}/enabled")
async def set_source_enabled(source_id: int, data: SourceEnabledInput, _: Principal = Depends(require_admin)):
    try:
        source = source_repository.set_enabled(source_id, data.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    notify_source_change()
    return {"status": "ok", "source": source}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, _: Principal = Depends(require_admin)):
    source = source_repository.delete(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    notify_source_change()
    return {"status": "ok", **source}
