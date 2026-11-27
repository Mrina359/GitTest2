from security import active_user_id

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from models.lists import ShoppingList, ListItem
from sqlmodel import Session, select
import secrets
import string

from database.connection import get_session
from models.users import User, Household, HouseholdMember
from security import hash_password, verify_password


user_router = APIRouter(tags=["Users & Households"])


# Схемы данных

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class HouseholdCreate(BaseModel):
    name: str


class InviteJoin(BaseModel):
    invite_code: str

class HouseholdRename(BaseModel):
    name: str
    
# Получение ID вошедшего пользователя

def get_current_user_id(request: Request, session: Session):
    user_id = active_user_id(request, session)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Необходимо войти в систему"
        )

    return user_id


# Регистрация

@user_router.post("/signup")
async def signup(
    data: UserCreate,
    request: Request,
    session: Session = Depends(get_session)
):
    email = str(data.email).strip().lower()
    display_name = data.display_name.strip()

    if not display_name:
        raise HTTPException(
            status_code=400,
            detail="Введите имя пользователя"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Пароль должен содержать не менее 6 символов"
        )

    user_exists = session.exec(
        select(User).where(User.email == email)
    ).first()

    if user_exists:
        raise HTTPException(
            status_code=409,
            detail="Email уже занят"
        )

    new_user = User(
        email=email,
        password=hash_password(data.password),
        display_name=display_name
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    request.session["is_admin"] = False
    request.session["user_id"] = new_user.id
    request.session["user_name"] = new_user.display_name

    return {
        "message": "Пользователь создан",
        "user_id": new_user.id
    }


# Вход

@user_router.post("/signin")
async def signin(
    data: UserLogin,
    request: Request,
    session: Session = Depends(get_session)
):
    email = str(data.email).strip().lower()

    user = session.exec(
        select(User).where(User.email == email)
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Неверный email или пароль"
        )

    valid, updated_hash = verify_password(
        data.password,
        user.password
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Неверный email или пароль"
        )

    # Если пароль был старым или его параметры хеширования обновились,
    # сохраняем новый хеш
    if user.is_blocked:
        request.session.clear()
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")

    if updated_hash:
        user.password = updated_hash
        session.add(user)
        session.commit()

    request.session["is_admin"] = user.is_admin
    request.session["user_id"] = user.id
    request.session["user_name"] = user.display_name

    return {
        "message": f"Добро пожаловать, {user.display_name}!",
        "user_id": user.id
    }


# Создание домохозяйства

@user_router.post("/household/create")
async def create_household(
    data: HouseholdCreate,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request, session)
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Введите название домохозяйства"
        )

    while True:
        code = "".join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(6)
        )

        existing = session.exec(
            select(Household).where(Household.invite_code == code)
        ).first()

        if not existing:
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
    session.refresh(household)

    return {
        "message": "Домохозяйство создано",
        "household_id": household.id,
        "invite_code": code
    }


# Вступление в домохозяйство

@user_router.post("/household/join")
async def join_household(
    data: InviteJoin,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request, session)
    invite_code = data.invite_code.strip().upper()

    household = session.exec(
        select(Household).where(
            Household.invite_code == invite_code
        )
    ).first()

    if not household:
        raise HTTPException(
            status_code=404,
            detail="Неверный код приглашения"
        )

    existing = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household.id,
            HouseholdMember.user_id == user_id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Вы уже состоите в этом домохозяйстве"
        )

    member = HouseholdMember(
        household_id=household.id,
        user_id=user_id,
        role="member"
    )

    session.add(member)
    session.commit()

    return {
        "message": f"Вы вступили в домохозяйство '{household.name}'",
        "household_id": household.id
    }


# ==========================================
# ПЕРЕИМЕНОВАНИЕ И УДАЛЕНИЕ ДОМОХОЗЯЙСТВА (API)
# ==========================================

@user_router.put("/household/{household_id}/rename")
async def rename_household(
    household_id: int,
    data: HouseholdRename,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request, session)

    household = session.get(Household, household_id)

    if not household:
        raise HTTPException(
            status_code=404,
            detail="Домохозяйство не найдено"
        )

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        raise HTTPException(
            status_code=403,
            detail="Только владелец может переименовать домохозяйство"
        )

    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Название не может быть пустым"
        )

    household.name = name
    session.add(household)
    session.commit()

    return {"message": "Домохозяйство переименовано"}


@user_router.delete("/household/{household_id}")
async def delete_household(
    household_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request, session)

    household = session.get(Household, household_id)

    if not household:
        raise HTTPException(
            status_code=404,
            detail="Домохозяйство не найдено"
        )

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        raise HTTPException(
            status_code=403,
            detail="Только владелец может удалить домохозяйство"
        )

    household_lists = session.exec(
        select(ShoppingList).where(
            ShoppingList.household_id == household_id
        )
    ).all()

    for shopping_list in household_lists:
        items = session.exec(
            select(ListItem).where(
                ListItem.list_id == shopping_list.id
            )
        ).all()

        for item in items:
            session.delete(item)

        session.delete(shopping_list)

    members = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id
        )
    ).all()

    for member in members:
        session.delete(member)

    session.delete(household)
    session.commit()

    return {"message": "Домохозяйство и связанные данные удалены"}
