import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.refresh_token import RefreshToken
from ..models.user import User
from .deps import get_db, require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    username: str


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _ensure_admin_user(db: AsyncSession) -> None:
    """Create default admin user on first startup if users table is empty."""
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    pw_hash = settings.admin_password_hash if settings.admin_password_hash else _hash_password("admin")
    if not settings.admin_password_hash:
        logger.warning(
            "Creating default admin user with password 'admin'. "
            "Set ADMIN_PASSWORD_HASH in .env for production."
        )

    admin = User(username=settings.admin_username, password_hash=pw_hash, is_active=True)
    db.add(admin)
    await db.commit()
    logger.info("Created default admin user '%s'", settings.admin_username)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)):
    await _ensure_admin_user(db)

    result = await db.execute(
        select(User).where(User.username == req.username, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    access_token = _create_access_token(user.username)

    raw_refresh = secrets.token_urlsafe(48)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days),
        revoked=False,
    )
    db.add(rt)
    await db.commit()

    logger.info("User '%s' logged in", user.username)
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = _hash_token(req.refresh_token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > now,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=401, detail="Недействительный или просроченный refresh token")

    user_result = await db.execute(
        select(User).where(User.id == rt.user_id, User.is_active == True)  # noqa: E712
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    rt.revoked = True

    new_access = _create_access_token(user.username)
    new_raw_refresh = secrets.token_urlsafe(48)
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(new_raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days),
        revoked=False,
    )
    db.add(new_rt)
    await db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_raw_refresh)


@router.post("/logout")
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = _hash_token(req.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()
    return {"detail": "Выход выполнен"}


@router.get("/me", response_model=UserResponse)
async def me(username: str = Depends(require_auth)):
    return UserResponse(username=username)
