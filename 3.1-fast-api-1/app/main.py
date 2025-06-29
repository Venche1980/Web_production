from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from app.models import Advertisement, AdvertisementCreate, AdvertisementUpdate
from app.database import db

# Создаем приложение FastAPI
app = FastAPI(
    title="Сервис объявлений",
    description="API для создания и управления объявлениями купли/продажи",
    version="1.0.0"
)


# Главная страница
@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в сервис объявлений!"}


# Создание объявления
@app.post("/advertisement", response_model=Advertisement)
def create_advertisement(advertisement: AdvertisementCreate):
    """Создать новое объявление"""
    new_ad = Advertisement(**advertisement.dict())
    created_ad = db.create_advertisement(new_ad)
    return created_ad


# Получение объявления по ID
@app.get("/advertisement/{advertisement_id}", response_model=Advertisement)
def get_advertisement(advertisement_id: int):
    """Получить объявление по ID"""
    ad = db.get_advertisement(advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return ad


# Обновление объявления
@app.patch("/advertisement/{advertisement_id}", response_model=Advertisement)
def update_advertisement(advertisement_id: int, update_data: AdvertisementUpdate):
    """Обновить существующее объявление"""
    updated_ad = db.update_advertisement(advertisement_id, update_data.dict(exclude_unset=True))
    if not updated_ad:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return updated_ad


# Удаление объявления
@app.delete("/advertisement/{advertisement_id}")
def delete_advertisement(advertisement_id: int):
    """Удалить объявление"""
    success = db.delete_advertisement(advertisement_id)
    if not success:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return {"message": "Объявление успешно удалено"}


# Поиск объявлений
@app.get("/advertisement", response_model=List[Advertisement])
def search_advertisements(
        title: Optional[str] = Query(None, description="Поиск по заголовку"),
        description: Optional[str] = Query(None, description="Поиск по описанию"),
        author: Optional[str] = Query(None, description="Поиск по автору"),
        min_price: Optional[float] = Query(None, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, description="Максимальная цена")
):
    """Поиск объявлений по различным параметрам"""
    filters = {
        "title": title,
        "description": description,
        "author": author,
        "min_price": min_price,
        "max_price": max_price
    }

    # Убираем None значения
    filters = {k: v for k, v in filters.items() if v is not None}

    results = db.search_advertisements(filters)
    return results


# Для проверки работы API
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)