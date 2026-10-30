from sqlmodel import SQLModel, Session, create_engine
from models.events import Event 

database_file = "planner.db"
database_connection_string = f"sqlite:///{database_file}"
connect_args = {"check_same_thread": False}
engine_url = create_engine(
    database_connection_string,
    echo=True,
    connect_args=connect_args
)
def conn():
    """Создаёт базу и все таблицы, если их ещё нет."""
    SQLModel.metadata.create_all(engine_url)
def get_session():
    """Генератор сессий — используется через Depends в маршрутах."""
    with Session(engine_url) as session:
        yield session