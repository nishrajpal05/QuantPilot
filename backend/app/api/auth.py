from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(
        text("SELECT id FROM public.profiles WHERE email = :email"),
        {"email": body.email},
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(body.password)
    result = db.execute(
        text("""
            INSERT INTO public.profiles (id, email, full_name, password_hash)
            VALUES (uuid_generate_v4(), :email, :full_name, :password_hash)
            RETURNING id
        """),
        {"email": body.email, "full_name": body.full_name, "password_hash": hashed},
    )
    user_id = str(result.fetchone()[0])
    db.commit()
    token = create_access_token(user_id, body.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT id, password_hash FROM public.profiles WHERE email = :email"),
        {"email": body.email},
    ).fetchone()
    if not row or not verify_password(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(row.id), body.email)
    return TokenResponse(access_token=token)


@router.get("/me")
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT id, email, full_name, plan, backtests_this_month FROM public.profiles WHERE id = :id"),
        {"id": current_user["sub"]},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": str(row.id), "email": row.email, "full_name": row.full_name,
            "plan": row.plan, "backtests_this_month": row.backtests_this_month}
