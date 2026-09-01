from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from admin.api import router as admin_router
from auth.api import router as auth_router
from catalog.api import router as catalog_router
from core.lifecycle import ApplicationLifecycle
from delivery.api import router as delivery_router, share_router
from telegram.api import router as telegram_router

WEB_INDEX = Path("/app/web/index.html")
ADMIN_SCRIPT = '<script src="/admin.js" defer></script>'


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
    if ADMIN_SCRIPT not in html:
        html = html.replace("</body>", f"{ADMIN_SCRIPT}</body>")
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

    @app.get("/admin.js", include_in_schema=False)
    async def admin_js():
        return FileResponse(
            "/app/web/admin.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )

    return app
