from sqlmodel import SQLModel, Session, create_engine

# Импортируем все модели, чтобы SQLModel увидел таблицы
from models.users import User, Household, HouseholdMember
from models.lists import ShoppingList, ListItem

# Создаём подключение к SQLite
database_file = "shopping.db"

engine = create_engine(
    f"sqlite:///{database_file}",
    echo=True,
    connect_args={"check_same_thread": False}
)

# Создание таблиц
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Создание сессии для работы с БД
def get_session():
    with Session(engine) as session:
        yield session