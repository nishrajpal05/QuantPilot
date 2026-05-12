from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api import auth, backtest, data

settings = get_settings()

app = FastAPI(
    title="QuantPilot API",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://quant-pilot-one.vercel.app/",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}