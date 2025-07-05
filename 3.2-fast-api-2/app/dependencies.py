from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.auth import get_current_user
from app.models import User, UserRole

# Security схема для Bearer токенов
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Получить текущего пользователя если токен есть"""
    if not credentials:
        return None

    user = await get_current_user(credentials.credentials, db)
    return user


async def get_current_active_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> User:
    """Получить авторизованного пользователя (обязательно)"""
    user = await get_current_user(credentials.credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_admin_user(
        current_user: User = Depends(get_current_active_user)
) -> User:
    """Проверить что пользователь админ"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user