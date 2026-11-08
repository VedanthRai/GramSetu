"""GramSetu FastAPI app: API + WebSocket + locally hosted demo portals + built frontend."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.config import REPO_ROOT
from app.core.logging import get_logger
from app.db.database import init_db
from app.demo_portals.clinic import router as clinic_router
from app.demo_portals.scheme import router as scheme_router
from app.services.browser.executor import MANAGER

log = get_logger("gramsetu")
DIST = REPO_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    await MANAGER.close()


app = FastAPI(title="GramSetu API", version="1.0.0", lifespan=lifespan)
app.include_router(api_router)
app.include_router(scheme_router)
app.include_router(clinic_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/portal/"):
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return resp


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Unexpected server error"}, status_code=500)


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file() and DIST in candidate.resolve().parents:
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
