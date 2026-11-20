
import secrets
import string

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database.connection import get_session
from models.lists import ShoppingList, ListItem
from models.users import User, Household, HouseholdMember
from security import hash_password, verify_password


ui_router = APIRouter(tags=["UI"])
templates = Jinja2Templates(directory="templates")


def get_home_context(request: Request, session: Session, error: str = None):
    user_id = request.session.get("user_id")

    user_households = session.exec(
        select(Household)
        .join(
            HouseholdMember,
            Household.id == HouseholdMember.household_id
        )
        .where(HouseholdMember.user_id == user_id)
    ).all()

    household_ids = [household.id for household in user_households]

    if household_ids:
        lists = session.exec(
            select(ShoppingList).where(
                ShoppingList.household_id.in_(household_ids)
            )
        ).all()
    else:
        lists = []

    return {
        "lists": lists,
        "user_name": request.session.get("user_name"),
        "user_households": user_households,
        "error": error
    }


def is_household_member(
    session: Session,
    household_id: int,
    user_id: int
):
    membership = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id
        )
    ).first()

    return membership is not None


@ui_router.get("/")
async def home(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    context = get_home_context(request, session)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context
    )


@ui_router.get("/ui/list/{list_id}")
async def view_list(
    list_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shop_list = session.get(ShoppingList, list_id)

    if not shop_list:
        return RedirectResponse(url="/", status_code=303)

    if not is_household_member(session, shop_list.household_id, user_id):
        return RedirectResponse(url="/", status_code=303)

    items = session.exec(
        select(ListItem).where(ListItem.list_id == list_id)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="list.html",
        context={
            "shop_list": shop_list,
            "items": items,
            "user_name": request.session.get("user_name")
        }
    )


@ui_router.post("/ui/list/{list_id}/add-item")
async def add_item_ui(
    list_id: int,
    request: Request,
    name: str = Form(...),
    quantity: float = Form(1.0),
    unit: str = Form("шт"),
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shop_list = session.get(ShoppingList, list_id)

    if not shop_list:
        return RedirectResponse(url="/", status_code=303)

    if not is_household_member(session, shop_list.household_id, user_id):
        return RedirectResponse(url="/", status_code=303)

    if shop_list.status != "active":
        return RedirectResponse(url=f"/ui/list/{list_id}", status_code=303)

    name = name.strip()
    unit = unit.strip()

    if not name or quantity <= 0 or not unit:
        return RedirectResponse(url=f"/ui/list/{list_id}", status_code=303)

    new_item = ListItem(
        list_id=list_id,
        name=name,
        quantity=quantity,
        unit=unit,
        added_by=user_id
    )

    session.add(new_item)
    session.commit()

    return RedirectResponse(url=f"/ui/list/{list_id}", status_code=303)


@ui_router.get("/ui/list/{list_id}/buy/{item_id}")
async def buy_item_ui(
    list_id: int,
    item_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shop_list = session.get(ShoppingList, list_id)
    item = session.get(ListItem, item_id)

    if not shop_list or not item:
        return RedirectResponse(url="/", status_code=303)

    if item.list_id != list_id:
        return RedirectResponse(url="/", status_code=303)

    if not is_household_member(session, shop_list.household_id, user_id):
        return RedirectResponse(url="/", status_code=303)

    if shop_list.status != "active":
        return RedirectResponse(url=f"/ui/list/{list_id}", status_code=303)

    item.status = "bought"
    session.add(item)
    session.commit()

    return RedirectResponse(url=f"/ui/list/{list_id}", status_code=303)


@ui_router.post("/ui/create-list")
async def create_list_ui(
    request: Request,
    title: str = Form(...),
    household_id: int = Form(...),
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    title = title.strip()

    if not title:
        return RedirectResponse(url="/", status_code=303)

    if not is_household_member(session, household_id, user_id):
        return RedirectResponse(url="/", status_code=303)

    new_list = ShoppingList(
        household_id=household_id,
        title=title,
        status="active"
    )

    session.add(new_list)
    session.commit()

    return RedirectResponse(url="/", status_code=303)


@ui_router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"is_signup": False}
    )


@ui_router.post("/login")
async def login_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    email = email.strip().lower()

    user = session.exec(
        select(User).where(User.email == email)
    ).first()

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Неверный email или пароль",
                "is_signup": False
            }
        )

    valid, updated_hash = verify_password(password, user.password)

    if not valid:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Неверный email или пароль",
                "is_signup": False
            }
        )

    if updated_hash:
        user.password = updated_hash
        session.add(user)
        session.commit()

    request.session["user_id"] = user.id
    request.session["user_name"] = user.display_name

    return RedirectResponse(url="/", status_code=303)


@ui_router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"is_signup": True}
    )


@ui_router.post("/signup")
async def signup_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    session: Session = Depends(get_session)
):
    email = email.strip().lower()
    display_name = display_name.strip()

    if not email or not password or not display_name:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Заполните все поля",
                "is_signup": True
            }
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Пароль должен содержать не менее 6 символов",
                "is_signup": True
            }
        )

    user_exists = session.exec(
        select(User).where(User.email == email)
    ).first()

    if user_exists:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Пользователь с таким email уже существует",
                "is_signup": True
            }
        )

    new_user = User(
        email=email,
        password=hash_password(password),
        display_name=display_name
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    request.session["user_id"] = new_user.id
    request.session["user_name"] = new_user.display_name

    return RedirectResponse(url="/", status_code=303)


@ui_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@ui_router.post("/ui/create-household")
async def create_household_ui(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    name = name.strip()

    if not name:
        return RedirectResponse(url="/", status_code=303)

    while True:
        code = "".join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        )

        existing_household = session.exec(
            select(Household).where(Household.invite_code == code)
        ).first()

        if not existing_household:
            break

    household = Household(
        name=name,
        invite_code=code
    )

    session.add(household)
    session.flush()

    member = HouseholdMember(
        household_id=household.id,
        user_id=user_id,
        role="owner"
    )

    session.add(member)
    session.commit()

    return RedirectResponse(url="/", status_code=303)


@ui_router.post("/ui/join-household")
async def join_household_ui(
    request: Request,
    invite_code: str = Form(...),
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    invite_code = invite_code.strip().upper()

    household = session.exec(
        select(Household).where(
            Household.invite_code == invite_code
        )
    ).first()

    if not household:
        context = get_home_context(
            request,
            session,
            error="Домохозяйство с таким кодом не найдено"
        )

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=context
        )

    existing = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household.id,
            HouseholdMember.user_id == user_id
        )
    ).first()

    if existing:
        context = get_home_context(
            request,
            session,
            error="Вы уже состоите в этом домохозяйстве"
        )

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=context
        )

    member = HouseholdMember(
        household_id=household.id,
        user_id=user_id,
        role="member"
    )

    session.add(member)
    session.commit()

    return RedirectResponse(url="/", status_code=303)

# ==========================================
# ПЕРЕИМЕНОВАНИЕ И УДАЛЕНИЕ ДОМОХОЗЯЙСТВ
# ==========================================

@ui_router.post("/ui/household/{household_id}/rename")
async def rename_household_ui(
    household_id: int,
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    household = session.get(Household, household_id)

    if not household:
        return RedirectResponse(url="/", status_code=303)

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        return RedirectResponse(url="/", status_code=303)

    name = name.strip()

    if not name:
        return RedirectResponse(url="/", status_code=303)

    household.name = name
    session.add(household)
    session.commit()

    return RedirectResponse(url="/", status_code=303)


@ui_router.post("/ui/household/{household_id}/delete")
async def delete_household_ui(
    household_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    household = session.get(Household, household_id)

    if not household:
        return RedirectResponse(url="/", status_code=303)

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        return RedirectResponse(url="/", status_code=303)

    # Получаем все списки домохозяйства
    household_lists = session.exec(
        select(ShoppingList).where(
            ShoppingList.household_id == household_id
        )
    ).all()

    # Удаляем товары каждого списка
    for shopping_list in household_lists:
        items = session.exec(
            select(ListItem).where(
                ListItem.list_id == shopping_list.id
            )
        ).all()

        for item in items:
            session.delete(item)

        session.delete(shopping_list)

    # Удаляем участников домохозяйства
    members = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id
        )
    ).all()

    for member in members:
        session.delete(member)

    # Удаляем само домохозяйство
    session.delete(household)

    session.commit()

    return RedirectResponse(url="/", status_code=303)

# ==========================================
# ПЕРЕИМЕНОВАНИЕ И УДАЛЕНИЕ СПИСКОВ
# ==========================================

@ui_router.post("/ui/list/{list_id}/rename")
async def rename_list_ui(
    list_id: int,
    request: Request,
    title: str = Form(...),
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shopping_list = session.get(ShoppingList, list_id)

    if not shopping_list:
        return RedirectResponse(url="/", status_code=303)

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == shopping_list.household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        return RedirectResponse(url="/", status_code=303)

    title = title.strip()

    if not title:
        return RedirectResponse(
            url=f"/ui/list/{list_id}",
            status_code=303
        )

    shopping_list.title = title

    session.add(shopping_list)
    session.commit()

    return RedirectResponse(
        url=f"/ui/list/{list_id}",
        status_code=303
    )


@ui_router.post("/ui/list/{list_id}/delete")
async def delete_list_ui(
    list_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shopping_list = session.get(ShoppingList, list_id)

    if not shopping_list:
        return RedirectResponse(url="/", status_code=303)

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == shopping_list.household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        return RedirectResponse(url="/", status_code=303)

    # Удаляем все товары списка
    items = session.exec(
        select(ListItem).where(
            ListItem.list_id == list_id
        )
    ).all()

    for item in items:
        session.delete(item)

    # Удаляем список
    session.delete(shopping_list)

    session.commit()

    return RedirectResponse(url="/", status_code=303)

# ==========================================
# ИЗМЕНЕНИЕ И УДАЛЕНИЕ ТОВАРОВ
# ==========================================

@ui_router.post("/ui/list/{list_id}/item/{item_id}/edit")
async def edit_item_ui(
    list_id: int,
    item_id: int,
    request: Request,
    name: str = Form(...),
    quantity: float = Form(...),
    unit: str = Form(...),
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shopping_list = session.get(ShoppingList, list_id)
    item = session.get(ListItem, item_id)

    if not shopping_list or not item or item.list_id != list_id:
        return RedirectResponse(url="/", status_code=303)

    if not is_household_member(
        session,
        shopping_list.household_id,
        user_id
    ):
        return RedirectResponse(url="/", status_code=303)

    if shopping_list.status != "active":
        return RedirectResponse(
            url=f"/ui/list/{list_id}",
            status_code=303
        )

    name = name.strip()
    unit = unit.strip()

    if not name or not unit or quantity <= 0:
        return RedirectResponse(
            url=f"/ui/list/{list_id}",
            status_code=303
        )

    if item.status == "removed":
        return RedirectResponse(
            url=f"/ui/list/{list_id}",
            status_code=303
        )

    item.name = name
    item.quantity = quantity
    item.unit = unit

    session.add(item)
    session.commit()

    return RedirectResponse(
        url=f"/ui/list/{list_id}",
        status_code=303
    )


@ui_router.post("/ui/list/{list_id}/item/{item_id}/delete")
async def delete_item_ui(
    list_id: int,
    item_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shopping_list = session.get(ShoppingList, list_id)
    item = session.get(ListItem, item_id)

    if not shopping_list or not item or item.list_id != list_id:
        return RedirectResponse(url="/", status_code=303)

    if not is_household_member(
        session,
        shopping_list.household_id,
        user_id
    ):
        return RedirectResponse(url="/", status_code=303)

    if shopping_list.status != "active":
        return RedirectResponse(
            url=f"/ui/list/{list_id}",
            status_code=303
        )

    item.status = "removed"

    session.add(item)
    session.commit()

    return RedirectResponse(
        url=f"/ui/list/{list_id}",
        status_code=303
    )


@ui_router.post("/ui/list/{list_id}/item/{item_id}/restore")
async def restore_item_ui(
    list_id: int,
    item_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    shopping_list = session.get(ShoppingList, list_id)
    item = session.get(ListItem, item_id)

    if not shopping_list or not item or item.list_id != list_id:
        return RedirectResponse(url="/", status_code=303)

    if not is_household_member(
        session,
        shopping_list.household_id,
        user_id
    ):
        return RedirectResponse(url="/", status_code=303)

    if shopping_list.status != "active":
        return RedirectResponse(
            url=f"/ui/list/{list_id}",
            status_code=303
        )

    item.status = "needed"

    session.add(item)
    session.commit()

    return RedirectResponse(
        url=f"/ui/list/{list_id}",
        status_code=303
    )
