from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from admin.api import router as admin_router
from auth.api import router as auth_router
from catalog.api import router as catalog_router
from core.lifecycle import ApplicationLifecycle
from download.api import router as delivery_router
from share.api import router as share_router
from telegram.api import router as telegram_router

APP_DIR = Path(__file__).resolve().parents[1]
ADMIN_DIST = APP_DIR / "frontend" / "dist"


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
    app.include_router(catalog_router)
    app.include_router(delivery_router)
    app.include_router(share_router)
    app.include_router(telegram_router)
    app.include_router(admin_router)

    @app.get("/", include_in_schema=False)
    async def home():
        return RedirectResponse(url="/admin/", status_code=307)

    # Keep the former URL working while moving its UI to the frontend SPA.
    @app.get("/web", include_in_schema=False)
    async def web():
        return RedirectResponse(url="/admin/", status_code=307)

    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/", include_in_schema=False)
    async def admin():
        index = ADMIN_DIST / "index.html"
        if not index.exists():
            return HTMLResponse("Admin frontend is not built.", status_code=503)
        return FileResponse(index, headers={"Cache-Control": "no-store"})

    if ADMIN_DIST.exists():
        app.mount("/admin", StaticFiles(directory=ADMIN_DIST, html=True), name="admin-static")

    return app
