from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api import auth, backtest, data, fyers

settings = get_settings()

app = FastAPI(
    title="QuantPilot API",
    version="2.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(auth.router,     prefix=PREFIX)
app.include_router(backtest.router, prefix=PREFIX)
app.include_router(data.router,     prefix=PREFIX)
app.include_router(fyers.router,    prefix=PREFIX)


@app.get("/")
def root():
    return {
        "name":      "QuantPilot API",
        "version":   "2.0.0",
        "status":    "running",
        "frontend":  "https://quant-pilot-one.vercel.app",
        "endpoints": [
            "POST /api/v1/auth/register",
            "POST /api/v1/auth/login",
            "GET  /api/v1/auth/me",
            "POST /api/v1/backtest",
            "GET  /api/v1/backtest/list",
            "GET  /api/v1/backtest/{id}",
            "GET  /api/v1/backtest/{id}/audit",
            "GET  /api/v1/data/symbols",
            "GET  /api/v1/data/ohlcv/{symbol}",
            "POST /api/v1/fyers/connect",
            "GET  /api/v1/fyers/callback",
            "GET  /api/v1/fyers/status",
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
