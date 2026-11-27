from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlalchemy import delete
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from database.connection import get_session
from models.users import User, Household, HouseholdMember
from models.lists import ShoppingList, ListItem
from security import active_user_id

admin_router = APIRouter(tags=["Admin"])
templates = Jinja2Templates(directory="templates")

def require_admin(request: Request, session: Session = Depends(get_session)):
    uid = active_user_id(request, session)
    user = session.get(User, uid) if uid else None
    if not user or not user.is_admin:
        raise HTTPException(403, "Доступ только для администратора")
    return user

def finish(request, message, error=False):
    request.session["admin_notice"] = [message, error]
    return RedirectResponse("/admin", status_code=303)

def find(session, model, ident):
    obj = session.get(model, ident)
    if obj is None:
        raise HTTPException(404, "Объект не найден")
    return obj

@admin_router.get("/admin")
def admin_panel(request: Request, q: str = "", session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    users = session.exec(select(User)).all()
    households = session.exec(select(Household)).all()
    lists = session.exec(select(ShoppingList)).all()
    items = session.exec(select(ListItem)).all()
    members = session.exec(select(HouseholdMember)).all()
    names = {u.id: u.display_name for u in users}
    q = q.strip()
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "users": [u for u in users if q.casefold() in (u.display_name + " " + u.email).casefold()],
        "households": households, "lists": lists, "items": items, "members": members,
        "names": names, "household_names": {h.id: h.name for h in households}, "q": q,
        "notice": request.session.pop("admin_notice", None),
        "stats": [("Пользователи", len(users)), ("Заблокированы", sum(u.is_blocked for u in users)), ("Домохозяйства", len(households)), ("Активные списки", sum(l.status == "active" for l in lists)), ("Архивные списки", sum(l.status == "archived" for l in lists)), ("Товары", sum(i.status != "removed" for i in items)), ("Куплено", sum(i.status == "bought" for i in items))]
    })

@admin_router.post("/admin/users/{uid}/edit")
def edit_user(uid: int, request: Request, display_name: str = Form(...), email: str = Form(...), session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    user = find(session, User, uid)
    if user.is_admin:
        return finish(request, "Аккаунты администраторов защищены", True)
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email.strip().lower()))
    except ValidationError:
        return finish(request, "Некорректный email", True)
    if not display_name.strip():
        return finish(request, "Имя не может быть пустым", True)
    user.display_name = display_name.strip()
    user.email = email
    try:
        session.add(user)
        session.commit()
    except IntegrityError:
        session.rollback()
        return finish(request, "Email уже занят", True)
    return finish(request, "Пользователь изменён")

@admin_router.post("/admin/users/{uid}/block")
def block_user(uid: int, request: Request, session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    user = find(session, User, uid)
    if user.is_admin:
        return finish(request, "Нельзя блокировать администратора", True)
    user.is_blocked = not user.is_blocked
    session.add(user)
    session.commit()
    return finish(request, "Статус пользователя изменён")

@admin_router.post("/admin/users/{uid}/delete")
def delete_user(uid: int, request: Request, session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    user = find(session, User, uid)
    if user.is_admin:
        return finish(request, "Нельзя удалить администратора", True)
    if session.exec(select(HouseholdMember).where(HouseholdMember.user_id == uid)).first() or session.exec(select(ListItem).where(ListItem.added_by == uid)).first():
        return finish(request, "Есть связанные данные. Используйте блокировку вместо удаления.", True)
    session.delete(user)
    session.commit()
    return finish(request, "Пользователь удалён")

@admin_router.post("/admin/households/{hid}/rename")
def rename_household(hid: int, request: Request, name: str = Form(...), session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    h = find(session, Household, hid)
    if not name.strip():
        return finish(request, "Введите название", True)
    h.name = name.strip()
    session.add(h)
    session.commit()
    return finish(request, "Домохозяйство переименовано")

@admin_router.post("/admin/households/{hid}/delete")
def delete_household(hid: int, request: Request, session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    h = find(session, Household, hid)
    for l in session.exec(select(ShoppingList).where(ShoppingList.household_id == hid)).all():
        session.execute(delete(ListItem).where(ListItem.list_id == l.id))
    session.execute(delete(ShoppingList).where(ShoppingList.household_id == hid))
    session.execute(delete(HouseholdMember).where(HouseholdMember.household_id == hid))
    session.delete(h)
    session.commit()
    return finish(request, "Домохозяйство удалено")

@admin_router.post("/admin/lists/{lid}/rename")
def rename_list(lid: int, request: Request, title: str = Form(...), session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    l = find(session, ShoppingList, lid)
    if not title.strip():
        return finish(request, "Введите название", True)
    l.title = title.strip()
    session.add(l)
    session.commit()
    return finish(request, "Список переименован")

@admin_router.post("/admin/lists/{lid}/status")
def change_status(lid: int, request: Request, session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    l = find(session, ShoppingList, lid)
    l.status = "archived" if l.status == "active" else "active"
    session.add(l)
    session.commit()
    return finish(request, "Статус списка изменён")

@admin_router.post("/admin/lists/{lid}/delete")
def delete_list(lid: int, request: Request, session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    l = find(session, ShoppingList, lid)
    session.execute(delete(ListItem).where(ListItem.list_id == lid))
    session.delete(l)
    session.commit()
    return finish(request, "Список удалён")
