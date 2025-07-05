from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app import models, schemas
from app.auth import get_password_hash


# Функции для работы с пользователями

async def get_user(db: AsyncSession, user_id: int):
    """Получить пользователя по id"""
    result = await db.execute(
        select(models.User).filter(models.User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str):
    """Получить пользователя по username"""
    result = await db.execute(
        select(models.User).filter(models.User.username == username)
    )
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession):
    """Получить всех пользователей"""
    result = await db.execute(select(models.User))
    return result.scalars().all()


async def create_user(db: AsyncSession, user: schemas.UserCreate):
    """Создать пользователя"""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate):
    """Обновить пользователя"""
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(db_user, field, value)

    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: int):
    """Удалить пользователя"""
    db_user = await get_user(db, user_id)
    if not db_user:
        return False

    await db.delete(db_user)
    await db.commit()
    return True


# Функции для работы с объявлениями

async def get_advertisement(db: AsyncSession, ad_id: int):
    """Получить объявление по id"""
    result = await db.execute(
        select(models.Advertisement).filter(models.Advertisement.id == ad_id)
    )
    return result.scalar_one_or_none()


async def get_advertisements(
        db: AsyncSession,
        title: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
):
    """Поиск объявлений с фильтрами"""
    query = select(models.Advertisement)

    if title:
        query = query.filter(models.Advertisement.title.contains(title))
    if description:
        query = query.filter(models.Advertisement.description.contains(description))
    if author:
        query = query.filter(models.Advertisement.author.contains(author))
    if min_price is not None:
        query = query.filter(models.Advertisement.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Advertisement.price <= max_price)

    result = await db.execute(query)
    return result.scalars().all()


async def create_advertisement(
        db: AsyncSession,
        ad: schemas.AdvertisementCreate,
        owner_id: int
):
    """Создать объявление"""
    db_ad = models.Advertisement(
        **ad.dict(),
        owner_id=owner_id
    )
    db.add(db_ad)
    await db.commit()
    await db.refresh(db_ad)
    return db_ad


async def update_advertisement(
        db: AsyncSession,
        ad_id: int,
        ad_update: schemas.AdvertisementUpdate
):
    """Обновить объявление"""
    db_ad = await get_advertisement(db, ad_id)
    if not db_ad:
        return None

    update_data = ad_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_ad, field, value)

    await db.commit()
    await db.refresh(db_ad)
    return db_ad


async def delete_advertisement(db: AsyncSession, ad_id: int):
    """Удалить объявление"""
    db_ad = await get_advertisement(db, ad_id)
    if not db_ad:
        return False

    await db.delete(db_ad)
    await db.commit()
    return True