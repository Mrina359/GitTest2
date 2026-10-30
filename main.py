from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
from database.connection import conn
from routes.users import user_router
from routes.events import event_router
from routes.admin import admin_router 
import uvicorn

app = FastAPI(
    title="Планировщик событий Ишмухаметовой М.Р.",
    description="Приложение с базой данных SQLite и админ-панелью",
    version="1.0.0"
)
app.add_middleware(SessionMiddleware, secret_key="super-secret-key-12345")

app.include_router(user_router, prefix="/user")
app.include_router(event_router, prefix="/event")
app.include_router(admin_router, prefix="/admin") 

@app.on_event("startup")
def on_startup():
    conn()

@app.get("/")
async def home():
    return RedirectResponse(url="/admin/") # Теперь при заходе на главную кидает в админку

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)