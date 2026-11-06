# Удалите или закомментируйте эту строку:
# from motor.motor_asyncio import AsyncIOMotorClient

# Добавьте эту:
from pymongo import AsyncMongoClient
from typing import Any, List, Optional, Type
from beanie import init_beanie, Document, PydanticObjectId
#from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "mongodb://localhost:27017/planner"
    class Config:
        env_file = ".env"

settings = Settings()

async def init_db():
    # Было: client = AsyncIOMotorClient(settings.DATABASE_URL)
    client = AsyncMongoClient(settings.DATABASE_URL)

    from models.events import Event
    from models.users import User

    await init_beanie(
        database=client.planner,  # или client["planner"]
        document_models=[Event, User]
    )

# Класс Database (универсальный помощник для CRUD)
class Database:
    def __init__(self, model: Type[Document]):
        self.model = model

    async def save(self, document) -> None:
        await document.create()

    async def get(self, id: PydanticObjectId) -> Any:
        doc = await self.model.get(id)
        return doc if doc else False

    async def get_all(self) -> List[Any]:
        return await self.model.find_all().to_list()

    async def update(self, id: PydanticObjectId, body: BaseModel) -> Any:
        doc = await self.get(id)
        if not doc:
            return False
        des_body = body.model_dump(exclude_unset=True)
        if des_body:
            await doc.update({"$set": des_body})
        return doc

    async def delete(self, id: PydanticObjectId) -> bool:
        doc = await self.get(id)
        if not doc:
            return False
        await doc.delete()
        return True