
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database.connection import get_session
from models.users import User, Household
from models.lists import ShoppingList


admin_router = APIRouter(tags=["Admin"])
templates = Jinja2Templates(directory="templates")


@admin_router.get("/admin")
async def admin_panel(
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    user = session.get(User, user_id)

    if not user or not user.is_admin:
        return RedirectResponse(url="/", status_code=303)

    users = session.exec(select(User)).all()
    households = session.exec(select(Household)).all()
    lists = session.exec(select(ShoppingList)).all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "user_name": user.display_name,
            "users": users,
            "households": households,
            "lists": lists,
            "users_count": len(users),
            "households_count": len(households),
            "lists_count": len(lists)
        }
    )
