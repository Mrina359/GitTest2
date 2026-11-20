
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

from database.connection import create_db_and_tables
from routes.lists import list_router
from routes.users import user_router
from routes.ui import ui_router
from routes.admin import admin_router


app = FastAPI(
    title="Сервис совместных покупок",
    description="Веб-сервис для создания и совместного использования списков покупок"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

app.add_middleware(
    SessionMiddleware,
    secret_key="change-this-secret-key-before-deployment"
)

app.include_router(user_router, prefix="/users")
app.include_router(list_router, prefix="/lists")
app.include_router(ui_router)
app.include_router(admin_router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8080,
        reload=True
    )
