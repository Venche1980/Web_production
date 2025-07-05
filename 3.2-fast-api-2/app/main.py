from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app import models, schemas, crud
from app.database import engine, get_db, Base, AsyncSessionLocal
from app.auth import authenticate_user, create_access_token, get_password_hash
from app.dependencies import (
    get_current_user_optional,
    get_current_active_user,
    get_admin_user
)

# Создаем приложение
app = FastAPI(
    title="Сервис объявлений v2",
    description="API с авторизацией и PostgreSQL",
    version="2.0.0"
)


# Создаем таблицы при старте
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаем админа для тестирования
    async with AsyncSessionLocal() as db:
        admin = await crud.get_user_by_username(db, "admin")
        if not admin:
            admin_user = models.User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                role=models.UserRole.ADMIN
            )
            db.add(admin_user)
            await db.commit()
            print("Создан администратор: admin / admin123")


# === АВТОРИЗАЦИЯ ===

@app.post("/login", response_model=schemas.Token)
async def login(
        form_data: schemas.LoginRequest,
        db: AsyncSession = Depends(get_db)
):
    """Авторизация пользователя"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# === ПОЛЬЗОВАТЕЛИ ===

@app.get("/user/{user_id}", response_model=schemas.User)
async def get_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """Получить пользователя по ID"""
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/user", response_model=List[schemas.User])
async def get_users(
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_admin_user)
):
    """Получить всех пользователей (только админ)"""
    users = await crud.get_users(db)
    return users


@app.post("/user", response_model=schemas.User)
async def create_user(
        user: schemas.UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """Создать нового пользователя"""
    # Проверяем что username свободен
    db_user = await crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    return await crud.create_user(db, user)


@app.patch("/user/{user_id}", response_model=schemas.User)
async def update_user(
        user_id: int,
        user_update: schemas.UserUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Обновить пользователя"""
    # Проверка прав
    if current_user.role != models.UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    updated_user = await crud.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return updated_user


@app.delete("/user/{user_id}")
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Удалить пользователя"""
    # Проверка прав
    if current_user.role != models.UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    success = await crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted"}


# === ОБЪЯВЛЕНИЯ ===

@app.post("/advertisement", response_model=schemas.Advertisement)
async def create_advertisement(
        ad: schemas.AdvertisementCreate,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Создать объявление (нужна авторизация)"""
    return await crud.create_advertisement(db, ad, current_user.id)


@app.get("/advertisement/{advertisement_id}", response_model=schemas.Advertisement)
async def get_advertisement(
        advertisement_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """Получить объявление по ID"""
    ad = await crud.get_advertisement(db, advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return ad


@app.get("/advertisement", response_model=List[schemas.Advertisement])
async def search_advertisements(
        title: Optional[str] = Query(None, description="Поиск по заголовку"),
        description: Optional[str] = Query(None, description="Поиск по описанию"),
        author: Optional[str] = Query(None, description="Поиск по автору"),
        min_price: Optional[float] = Query(None, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, description="Максимальная цена"),
        db: AsyncSession = Depends(get_db),
        current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """Поиск объявлений"""
    ads = await crud.get_advertisements(
        db, title, description, author, min_price, max_price
    )
    return ads


@app.patch("/advertisement/{advertisement_id}", response_model=schemas.Advertisement)
async def update_advertisement(
        advertisement_id: int,
        ad_update: schemas.AdvertisementUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Обновить объявление"""
    # Получаем объявление
    ad = await crud.get_advertisement(db, advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # Проверка прав
    if current_user.role != models.UserRole.ADMIN and ad.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    updated_ad = await crud.update_advertisement(db, advertisement_id, ad_update)
    return updated_ad


@app.delete("/advertisement/{advertisement_id}")
async def delete_advertisement(
        advertisement_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Удалить объявление"""
    # Получаем объявление для проверки прав
    ad = await crud.get_advertisement(db, advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # Проверка прав
    if current_user.role != models.UserRole.ADMIN and ad.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await crud.delete_advertisement(db, advertisement_id)
    return {"message": "Advertisement deleted"}


@app.get("/")
def read_root():
    return {
        "message": "Сервис объявлений v2",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)