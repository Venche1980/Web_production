from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models import UserRole


# Схемы для пользователей
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class User(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


# Схемы для объявлений
class AdvertisementCreate(BaseModel):
    title: str
    description: str
    price: float = Field(gt=0)
    author: str


class AdvertisementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    author: Optional[str] = None


class Advertisement(BaseModel):
    id: int
    title: str
    description: str
    price: float
    author: str
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Схема для логина
class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str