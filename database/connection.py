from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import inspect, text

# Импортируем все модели базы данных
from models.users import User, Household, HouseholdMember
from models.lists import ShoppingList, ListItem


# Путь к базе данных в корне проекта
BASE_DIR = Path(__file__).resolve().parent.parent
database_file = BASE_DIR / "shopping.db"


# Подключение к SQLite
engine = create_engine(
    f"sqlite:///{database_file.as_posix()}",
    echo=False,
    connect_args={"check_same_thread": False}
)


# Обновление структуры существующей базы данных
def migrate_database():
    with engine.begin() as connection:
        inspector = inspect(connection)

        if "user" in inspector.get_table_names():
            columns = {
                column["name"]
                for column in inspector.get_columns("user")
            }

            if "is_admin" not in columns:
                connection.execute(
                    text(
                        'ALTER TABLE "user" '
                        'ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0'
                    )
                )

                print("Добавлено поле is_admin")

            if "is_blocked" not in columns:
                connection.execute(
                    text(
                        'ALTER TABLE "user" '
                        'ADD COLUMN is_blocked BOOLEAN NOT NULL DEFAULT 0'
                    )
                )

                print("Добавлено поле is_blocked")


# Создание таблиц и обновление базы данных
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    migrate_database()


# Создание сессии для работы с базой данных
def get_session():
    with Session(engine) as session:
        yield session