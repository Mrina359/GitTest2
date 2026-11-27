import os
import secrets
import uvicorn

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database.connection import create_db_and_tables
from routes.lists import list_router
from routes.users import user_router
from routes.ui import ui_router
from routes.admin import admin_router


# Инициализация приложения
@asynccontextmanager
async def lifespan(app: FastAPI):

    create_db_and_tables()

    print("База данных готова к работе")

    yield


app = FastAPI(
    title="Сервис совместных покупок",
    description=(
        "Веб-сервис для создания и совместного "
        "использования списков покупок"
    ),
    version="1.0.0",
    lifespan=lifespan
)


# Подключение статических файлов
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# Сессионная авторизация
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY") or secrets.token_hex(32)
)


# Подключение маршрутизаторов
app.include_router(user_router, prefix="/users")
app.include_router(list_router, prefix="/lists")
app.include_router(ui_router)
app.include_router(admin_router)


# Запуск приложения
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8080,
        reload=True
    )