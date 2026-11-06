from beanie import Document
from pydantic import EmailStr
from typing import Optional, List
from models.events import Event

class User(Document):
    email: EmailStr
    password: str
    events: Optional[List[Event]] = []

    class Settings:
        name = "users"

class UserSignIn(Document):
    email: EmailStr
    password: str
