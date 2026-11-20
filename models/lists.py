from typing import Optional
from sqlmodel import SQLModel, Field

class ShoppingList(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(foreign_key="household.id") # Привязка к семье
    title: str
    status: str = "active" # active или archived

class ListItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    list_id: int = Field(foreign_key="shoppinglist.id")
    name: str
    quantity: float = 1.0
    unit: str = "шт"
    status: str = "needed" # needed, bought, removed
    added_by: int
