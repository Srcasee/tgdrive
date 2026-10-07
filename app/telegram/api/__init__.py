from fastapi import APIRouter

from telegram.api.accounts import router as accounts_router
from telegram.api.dialogs import router as dialogs_router
from telegram.api.sources import router as sources_router
from telegram.api.runtime import router as runtime_router

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

router.include_router(accounts_router)
router.include_router(dialogs_router)
router.include_router(sources_router)
router.include_router(runtime_router)
