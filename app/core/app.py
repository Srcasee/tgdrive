from fastapi import FastAPI
from fastapi.responses import FileResponse

from core.lifecycle import ApplicationLifecycle
from files.api import router as files_router
from telegram.api import router as telegram_router


def create_app():
    app = FastAPI(title="tgdrive")
    lifecycle = ApplicationLifecycle()

    app.include_router(files_router)
    app.include_router(telegram_router)

    @app.get("/")
    async def home():
        return FileResponse("/app/web/index.html")

    @app.get("/web")
    async def web():
        return FileResponse("/app/web/index.html")

    @app.on_event("startup")
    async def startup():
        await lifecycle.startup()

    @app.on_event("shutdown")
    async def shutdown():
        await lifecycle.shutdown()

    app.state.lifecycle = lifecycle
    return app
