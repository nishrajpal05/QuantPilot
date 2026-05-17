import hashlib
import logging
import os

logger = logging.getLogger(__name__)


def generate_auth_url(app_id: str, redirect_uri: str, state: str) -> str:
  
    try:
        from fyers_apiv3 import fyersModel  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "fyers-apiv3 is not installed. Run: pip install fyers-apiv3==3.1.3"
        )

    session = fyersModel.SessionModel(
        client_id=app_id,
        secret_key="",          # not needed for URL generation step
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code",
        state=state,            # echoed back in callback — use user_id
    )

    url = session.generate_authcode()
    logger.info("Generated Fyers auth URL for app_id=%s", app_id)
    return url


def exchange_code_for_token(
    app_id: str,
    secret_key: str,
    auth_code: str,
    redirect_uri: str,
) -> str:
    
    try:
        from fyers_apiv3 import fyersModel  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "fyers-apiv3 is not installed. Run: pip install fyers-apiv3==3.1.3"
        )

    session = fyersModel.SessionModel(
        client_id=app_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code",
    )

    session.set_token(auth_code)
    resp = session.generate_token()

    if resp.get("s") != "ok":
        error_msg = resp.get("message", str(resp))
        logger.error("Fyers token exchange failed: %s", error_msg)
        raise RuntimeError(
            f"Fyers authentication failed: {error_msg}. "
            "Check that your App ID, Secret, and redirect URI are correct."
        )

    access_token = resp["access_token"]
    logger.info("Fyers token exchange successful for app_id=%s", app_id)
    return access_token


def is_token_valid(access_token: str | None) -> bool:
   
    return bool(access_token and len(access_token) > 10)