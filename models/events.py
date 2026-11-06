from beanie import Document
from typing import Optional, List

class Event(Document):
    title: str
    image: str
    description: str
    tags: List[str]
    location: str

    class Settings:
        name = "events"  # Название коллекции в MongoDB

class EventUpdate(Document):
    title: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    location: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Практическая работа Ишмухаметовой М.Р.",
                "image": "https://example.com/logo.png",
                "description": "ПЗ№7 по FastAPI",
                "tags": ["учеба", "fastapi", "практика"],
                "location": "Аудитория 6-111"
                }
        }
