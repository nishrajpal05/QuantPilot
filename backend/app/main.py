from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import get_settings
from app.api import auth, backtest, data

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB connectivity check on startup so Render logs show a clear error."""
    try:
        from app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection OK")
    except Exception as exc:
        logger.error("❌ Database connection FAILED on startup: %s", exc)
        # Don't crash startup — let /health report it instead
    yield


app = FastAPI(
    title="QuantPilot API",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)

_origins = settings.origins_list if settings.environment == "production" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["Content-Length"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router,     prefix=PREFIX)
app.include_router(backtest.router, prefix=PREFIX)
app.include_router(data.router,     prefix=PREFIX)


# ── Root ───────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "name":     "QuantPilot API",
        "version":  "0.1.0",
        "status":   "running",
        "frontend": "https://quant-pilot-one.vercel.app",
        "docs":     "unavailable in production",
        "developer": "Nishmeet Singh Rajpal",
        "endpoints": [
            "POST /api/v1/auth/register",
            "POST /api/v1/auth/login",
            "GET  /api/v1/auth/me",
            "POST /api/v1/backtest",
            "GET  /api/v1/backtest/list",
            "GET  /api/v1/backtest/{id}",
            "GET  /api/v1/data/symbols",
        ]
    }


# ── Health (also verifies DB) ──────────────────────────────────────────────────
@app.get("/health")
def health():
    try:
        from app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"
    return {"status": "ok", "version": "0.1.0", "db": db_status}