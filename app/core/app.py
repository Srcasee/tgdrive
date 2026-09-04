from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from admin.api import router as admin_router
from auth.api import router as auth_router
from catalog.api import router as catalog_router
from core.lifecycle import ApplicationLifecycle
from delivery.api import router as delivery_router, share_router
from telegram.api import router as telegram_router

APP_DIR = Path(__file__).resolve().parents[1]
WEB_INDEX = APP_DIR / "web" / "index.html"
ADMIN_INDEX = APP_DIR / "web" / "admin.html"
ADMIN_DIR = APP_DIR / "web" / "admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    lifecycle = ApplicationLifecycle()
    app.state.lifecycle = lifecycle
    await lifecycle.startup()
    try:
        yield
    finally:
        await lifecycle.shutdown()


def web_index_response():
    html = WEB_INDEX.read_text(encoding="utf-8")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


def admin_index_response():
    html = ADMIN_INDEX.read_text(encoding="utf-8")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


def create_app():
    app = FastAPI(title="tgdrive", lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(catalog_router)
    app.include_router(delivery_router)
    app.include_router(share_router)
    app.include_router(telegram_router)
    app.include_router(admin_router)

    @app.get("/", include_in_schema=False)
    async def home():
        return web_index_response()

    @app.get("/web", include_in_schema=False)
    async def web():
        return web_index_response()

    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/", include_in_schema=False)
    async def admin():
        return admin_index_response()

    app.mount("/admin", StaticFiles(directory=ADMIN_DIR), name="admin-static")
    return app
