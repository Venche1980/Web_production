from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Модель для создания объявления
class AdvertisementCreate(BaseModel):
    title: str = Field(..., description="Заголовок объявления")
    description: str = Field(..., description="Описание объявления")
    price: float = Field(..., gt=0, description="Цена (должна быть больше 0)")
    author: str = Field(..., description="Автор объявления")


# Модель для обновления объявления
class AdvertisementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    author: Optional[str] = None


# Полная модель объявления (с id и датой создания)
class Advertisement(AdvertisementCreate):
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }