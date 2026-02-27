from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import async_session
from ..models.user import User

ALGORITHM = "HS256"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def require_auth(authorization: str = Header(...)) -> str:
    """Return the username from the JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_user_id(
    username: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Return the user ID from the JWT token. Raises 401 if user not found."""
    result = await db.execute(
        select(User.id).where(User.username == username, User.is_active == True)  # noqa: E712
    )
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user_id
