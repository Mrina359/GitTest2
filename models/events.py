from typing import List
from pydantic import BaseModel


class Event(BaseModel):
    id: int
    title: str
    image: str
    description: str
    tags: List[str]
    location: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Практическая работа",
                "image": "https://example.com/logo.png",
                "description": "ПЗ№7 по FastAPI",
                "tags": ["учеба", "fastapi", "практика"],
                "location": "Аудитория 6-111"
                }
        }