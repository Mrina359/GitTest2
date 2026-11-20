
from sqlmodel import Session, select

from database.connection import engine
from models.users import User


email = input("Введите email существующего пользователя: ").strip().lower()

with Session(engine) as session:
    user = session.exec(
        select(User).where(User.email == email)
    ).first()

    if not user:
        print("Пользователь с таким email не найден.")
    else:
        user.is_admin = True
        session.add(user)
        session.commit()

        print(f"Пользователь {user.display_name} теперь администратор.")
