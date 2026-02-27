import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db, require_auth
from ..models.user import User
from ..schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(select(User).order_by(User.id))
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    exists = await db.execute(select(User.id).where(User.username == req.username))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Пользователь с таким именем уже существует")

    pw_hash = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(username=req.username, password_hash=pw_hash, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(require_auth),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await db.delete(user)
    await db.commit()
    return {"message": f"Пользователь '{user.username}' удалён"}
