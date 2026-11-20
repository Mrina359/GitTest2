from database.connection import conn, engine_url
from sqlmodel import Session
from models.lists import ShoppingList

conn()
with Session(engine_url) as session:
    shop_list = ShoppingList(household_id=1, title="Мой первый список")
    session.add(shop_list)
    session.commit()
    print(f"Список создан с ID: {shop_list.id}")