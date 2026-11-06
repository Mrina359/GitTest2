from beanie import Document
from typing import Optional, List

class Event(Document):
    title: str
    image: str
    description: str
    tags: List[str]
    location: str

    class Settings:
        name = "events"

from pydantic import BaseModel 

class EventUpdate(BaseModel):  # <-- Теперь BaseModel
    title: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    location: Optional[str] = None