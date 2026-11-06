from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from database.connection import init_db
from routes.users import user_router
from routes.events import event_router
import uvicorn

app = FastAPI(
    title="Планировщик событий Ишмухаметовой М.Р. (MongoDB)",
    description="Приложение с базой данных NoSQL (Beanie)",
    version="1.0.0"
)

app.include_router(user_router, prefix="/user")
app.include_router(event_router, prefix="/event")

# Запускаем инициализацию базы при старте приложения
@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/")
async def home():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)