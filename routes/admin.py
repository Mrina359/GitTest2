from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database.connection import engine_url, get_session 
from models.events import Event
from models.users import User

admin_router = APIRouter(tags=["Admin"])
templates = Jinja2Templates(directory="templates")

#АВТОРИЗАЦИЯ

@admin_router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@admin_router.post("/login")
async def login_action(
    request: Request, 
    email: str = Form(...), 
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    # Ищем пользователя в базе
    user = session.exec(select(User).where(User.email == email)).first()
    
    if not user or user.password != password:
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Неверный email или пароль"}
        )
    
    # Сохраняем пользователя в сессию (куки)
    request.session["user"] = user.email
    return RedirectResponse(url="/admin/", status_code=303)

@admin_router.get("/logout")
async def logout(request: Request):
    request.session.clear()  # Очищаем сессию
    return RedirectResponse(url="/admin/login", status_code=303)


#ПАНЕЛЬ АДМИНИСТРАТОРА

@admin_router.get("/")
async def admin_panel(request: Request):
    # Проверяем, вошел ли админ (защита от посторонних)
    if "user" not in request.session:
        return RedirectResponse(url="/admin/login", status_code=303)

    with Session(engine_url) as session:
        statement = select(Event)
        all_events = session.exec(statement).all()
        
        # Получаем пользователей из БД
        all_users = session.exec(select(User)).all()
    
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"events": all_events, "users": all_users}
    )

@admin_router.get("/delete-event/{id}")
async def admin_delete_event(id: int, request: Request):
    # Тоже защищаем удаление от неавторизованных
    if "user" not in request.session:
        return RedirectResponse(url="/admin/login", status_code=303)

    with Session(engine_url) as session:
        event = session.get(Event, id)
        if event:
            session.delete(event)
            session.commit()
    
    # После удаления возвращаемся на главную страницу админки
    return RedirectResponse(url="/admin/", status_code=303)