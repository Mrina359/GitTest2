from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import EmailStr

# Таблица для базы данных
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)  # unique=True запретит дубликаты email
    password: str

# Модель для регистрации (принимает данные)
class NewUser(SQLModel):
    email: EmailStr
    password: str

# Модель для входа (принимает данные)
class UserSignIn(SQLModel):
    email: EmailStr
    password: str