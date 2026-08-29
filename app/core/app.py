from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse

from admin.api import router as admin_router
from auth.api import router as auth_router
from core.lifecycle import ApplicationLifecycle
from files.api import router as files_router
from telegram.api import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    lifecycle = ApplicationLifecycle()
    app.state.lifecycle = lifecycle
    await lifecycle.startup()
    try:
        yield
    finally:
        await lifecycle.shutdown()


def create_app():
    app = FastAPI(title="tgdrive", lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(files_router)
    app.include_router(telegram_router)
    app.include_router(admin_router)

    @app.get("/")
    async def home():
        return FileResponse("/app/web/index.html")

    @app.get("/web")
    async def web():
        return FileResponse("/app/web/index.html")

    return app
