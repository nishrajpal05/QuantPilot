from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/fyers", tags=["fyers"])


class FyersConnectRequest(BaseModel):
    app_id:      str
    secret_key:  str
    redirect_uri: str


@router.post("/connect")
def fyers_connect(
    body:         FyersConnectRequest,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user),
):
    """
    Step 1: User provides their Fyers App ID + Secret.
    Returns the Fyers OAuth2 login URL — frontend redirects user there.
    """
    try:
        from app.data.fyers_auth import generate_auth_url
    except ImportError:
        raise HTTPException(status_code=503, detail="Fyers module not available — merge data-risk-v2 branch.")

    # Store app_id + secret temporarily (needed for token exchange in callback)
    db.execute(
        text("""
            UPDATE public.profiles
            SET fyers_app_id = :app_id, fyers_secret_key = :secret
            WHERE id = :uid
        """),
        {"app_id": body.app_id, "secret": body.secret_key, "uid": current_user["sub"]},
    )
    db.commit()

    auth_url = generate_auth_url(
        app_id=body.app_id,
        redirect_uri=body.redirect_uri,
        state=current_user["sub"],   # pass user_id as state — returned in callback
    )
    return {"auth_url": auth_url}


@router.get("/callback")
def fyers_callback(
    auth_code: str,
    state:     str,      # user_id passed back from Fyers
    db:        Session = Depends(get_db),
):
    """
    Step 2: Fyers redirects here after user logs in.
    Exchange auth_code → access token and store it.
    """
    try:
        from app.data.fyers_auth import exchange_code_for_token
        from app.data.db import save_fyers_credentials
    except ImportError:
        raise HTTPException(status_code=503, detail="Fyers module not available.")

    # Retrieve stored app_id + secret for this user
    row = db.execute(
        text("SELECT fyers_app_id, fyers_secret_key FROM public.profiles WHERE id=:uid"),
        {"uid": state},
    ).fetchone()

    if not row or not row.fyers_app_id:
        raise HTTPException(status_code=400, detail="Fyers credentials not found. Run /fyers/connect first.")

    redirect_uri = f"{settings.allowed_origins.split(',')[0]}/fyers/callback"

    try:
        access_token = exchange_code_for_token(
            app_id=row.fyers_app_id,
            secret_key=row.fyers_secret_key,
            auth_code=auth_code,
            redirect_uri=redirect_uri,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")

    save_fyers_credentials(state, row.fyers_app_id, row.fyers_secret_key, access_token)

    return {"status": "connected", "message": "Fyers account connected successfully."}


@router.get("/status")
def fyers_status(
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user),
):
    """Check if current user has a connected Fyers account."""
    row = db.execute(
        text("SELECT fyers_app_id, fyers_connected_at FROM public.profiles WHERE id=:uid"),
        {"uid": current_user["sub"]},
    ).fetchone()

    connected = bool(row and row.fyers_app_id)
    return {
        "connected":    connected,
        "connected_at": str(row.fyers_connected_at) if (row and row.fyers_connected_at) else None,
        "note":         "Access tokens expire daily — reconnect if backtests fail with auth errors." if connected else "Connect your Fyers account to enable intraday backtesting.",
    }
