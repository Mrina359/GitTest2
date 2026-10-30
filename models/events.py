from typing import List, Optional
from sqlmodel import SQLModel, Field, Column, JSON


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    image: str
    description: str
    tags: List[str] = Field(sa_column=Column(JSON))
    location: str

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


class EventUpdate(SQLModel):
    title: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    location: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Практическая работа Ишмухаметовой М.Р. (обновлено)",
                "location": "Аудитория 6-111"
            }
        }