import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import settings
from .deps import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

ALGORITHM = "HS256"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str


def _verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        # No hash set — accept default password "admin"
        return plain == "admin"
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest):
    if req.username != settings.admin_username:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not _verify_password(req.password, settings.admin_password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = _create_token(req.username)
    logger.info("User '%s' logged in", req.username)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(username: str = Depends(require_auth)):
    return UserResponse(username=username)
