
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Request
from database.connection import get_session
from models.lists import ShoppingList, ListItem
from models.users import HouseholdMember


list_router = APIRouter(tags=["Shopping Lists"])


# Схемы данных

class ListCreate(BaseModel):
    household_id: int
    title: str


class ItemCreate(BaseModel):
    name: str
    quantity: float = 1.0
    unit: str = "шт"

class ListRename(BaseModel):
    title: str


class ItemUpdate(BaseModel):
    name: str
    quantity: float
    unit: str

# Получение ID вошедшего пользователя

def get_current_user_id(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Необходимо войти в систему"
        )

    return user_id


# Проверка членства в домохозяйстве

def is_household_member(
    session: Session,
    household_id: int,
    user_id: int
):
    member = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id
        )
    ).first()

    return member is not None


# Создание списка покупок

@list_router.post("/create")
async def create_list(
    data: ListCreate,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    title = data.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Введите название списка"
        )

    if not is_household_member(
        session,
        data.household_id,
        user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Вы не состоите в этом домохозяйстве"
        )

    new_list = ShoppingList(
        household_id=data.household_id,
        title=title,
        status="active"
    )

    session.add(new_list)
    session.commit()
    session.refresh(new_list)

    return {
        "message": "Список создан",
        "list_id": new_list.id
    }


# Добавление товара

@list_router.post("/{list_id}/item")
async def add_item(
    list_id: int,
    data: ItemCreate,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    shopping_list = session.get(ShoppingList, list_id)

    if not shopping_list:
        raise HTTPException(
            status_code=404,
            detail="Список не найден"
        )

    if not is_household_member(
        session,
        shopping_list.household_id,
        user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этому списку"
        )

    if shopping_list.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Нельзя добавлять товары в архивный список"
        )

    name = data.name.strip()
    unit = data.unit.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Введите название товара"
        )

    if not unit:
        raise HTTPException(
            status_code=400,
            detail="Введите единицу измерения"
        )

    if data.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Количество должно быть больше нуля"
        )

    new_item = ListItem(
        list_id=list_id,
        name=name,
        quantity=data.quantity,
        unit=unit,
        status="needed",
        added_by=user_id
    )

    session.add(new_item)
    session.commit()
    session.refresh(new_item)

    return {
        "message": f"Позиция '{new_item.name}' добавлена",
        "item": new_item
    }


# Получение содержимого списка

@list_router.get("/{list_id}")
async def get_list(
    list_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    shopping_list = session.get(ShoppingList, list_id)

    if not shopping_list:
        raise HTTPException(
            status_code=404,
            detail="Список не найден"
        )

    if not is_household_member(
        session,
        shopping_list.household_id,
        user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этому списку"
        )

    items = session.exec(
        select(ListItem).where(
            ListItem.list_id == list_id
        )
    ).all()

    return {
        "list_id": shopping_list.id,
        "title": shopping_list.title,
        "status": shopping_list.status,
        "items": items
    }


# Архивация списка (только для владельца домохозяйства)

@list_router.put("/{list_id}/archive")
async def archive_list(
    list_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    shopping_list = session.get(ShoppingList, list_id)

    if not shopping_list:
        raise HTTPException(
            status_code=404,
            detail="Список не найден"
        )

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == shopping_list.household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        raise HTTPException(
            status_code=403,
            detail="Только владелец может архивировать список"
        )

    if shopping_list.status == "archived":
        raise HTTPException(
            status_code=400,
            detail="Список уже находится в архиве"
        )

    shopping_list.status = "archived"

    session.add(shopping_list)
    session.commit()

    return {
        "message": "Список архивирован"
    }


# ==========================================
# ПЕРЕИМЕНОВАНИЕ И УДАЛЕНИЕ СПИСКОВ (API)
# ==========================================

@list_router.put("/{list_id}/rename")
async def rename_list(
    list_id: int,
    data: ListRename,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    shopping_list = session.get(ShoppingList, list_id)

    if not shopping_list:
        raise HTTPException(
            status_code=404,
            detail="Список не найден"
        )

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == shopping_list.household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        raise HTTPException(
            status_code=403,
            detail="Только владелец может переименовать список"
        )

    title = data.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Название не может быть пустым"
        )

    shopping_list.title = title
    session.add(shopping_list)
    session.commit()

    return {"message": "Список переименован"}


@list_router.delete("/{list_id}")
async def delete_list(
    list_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    shopping_list = session.get(ShoppingList, list_id)

    if not shopping_list:
        raise HTTPException(
            status_code=404,
            detail="Список не найден"
        )

    owner = session.exec(
        select(HouseholdMember).where(
            HouseholdMember.household_id == shopping_list.household_id,
            HouseholdMember.user_id == user_id,
            HouseholdMember.role == "owner"
        )
    ).first()

    if not owner:
        raise HTTPException(
            status_code=403,
            detail="Только владелец может удалить список"
        )

    items = session.exec(
        select(ListItem).where(
            ListItem.list_id == list_id
        )
    ).all()

    for item in items:
        session.delete(item)

    session.delete(shopping_list)
    session.commit()

    return {"message": "Список и его товары удалены"}


# ==========================================
# ИЗМЕНЕНИЕ И УДАЛЕНИЕ ТОВАРОВ (API)
# ==========================================

@list_router.put("/{list_id}/item/{item_id}")
async def update_item(
    list_id: int,
    item_id: int,
    data: ItemUpdate,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    shopping_list = session.get(ShoppingList, list_id)
    item = session.get(ListItem, item_id)

    if not shopping_list or not item or item.list_id != list_id:
        raise HTTPException(
            status_code=404,
            detail="Список или товар не найден"
        )

    if not is_household_member(
        session,
        shopping_list.household_id,
        user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Нет доступа к списку"
        )

    if shopping_list.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Нельзя изменять архивный список"
        )

    if item.status == "removed":
        raise HTTPException(
            status_code=400,
            detail="Удалённый товар нельзя редактировать"
        )

    name = data.name.strip()
    unit = data.unit.strip()

    if not name or not unit or data.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Проверьте название, количество и единицу измерения"
        )

    item.name = name
    item.quantity = data.quantity
    item.unit = unit

    session.add(item)
    session.commit()

    return {"message": "Товар изменён"}


@list_router.delete("/{list_id}/item/{item_id}")
async def delete_item(
    list_id: int,
    item_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = get_current_user_id(request)

    shopping_list = session.get(ShoppingList, list_id)
    item = session.get(ListItem, item_id)

    if not shopping_list or not item or item.list_id != list_id:
        raise HTTPException(
            status_code=404,
            detail="Список или товар не найден"
        )

    if not is_household_member(
        session,
        shopping_list.household_id,
        user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Нет доступа к списку"
        )

    if shopping_list.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Нельзя изменять архивный список"
        )

    item.status = "removed"

    session.add(item)
    session.commit()

    return {"message": "Товар удалён из списка"}
