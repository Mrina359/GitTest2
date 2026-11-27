from getpass import getpass

from sqlmodel import Session, select
from pydantic import EmailStr, TypeAdapter, ValidationError

from database.connection import engine, create_db_and_tables
from models.users import User
from security import hash_password


def main():

    # Создаём или обновляем базу данных
    create_db_and_tables()

    print("=" * 45)
    print("Создание администратора сервиса ВместеКупим")
    print("=" * 45)

    email = input("Введите email: ").strip().lower()

    try:
        email = str(TypeAdapter(EmailStr).validate_python(email))
    except ValidationError:
        print("Некорректный email.")
        return

    with Session(engine) as session:

        user = session.exec(
            select(User).where(User.email == email)
        ).first()

        # Если пользователь уже существует
        if user:

            if user.is_admin:
                print("Пользователь уже является администратором.")
                return

            if user.is_blocked:
                print("Нельзя назначить администратором заблокированного пользователя.")
                return

            answer = input(
                "Пользователь существует. "
                "Назначить администратором? (y/n): "
            ).strip().lower()

            if answer not in ("y", "yes", "да", "д"):
                print("Операция отменена.")
                return

            user.is_admin = True

            session.add(user)
            session.commit()

            print(
                f"Пользователь {user.display_name} "
                "теперь является администратором."
            )

            return

        # Если пользователя нет — создаём новый аккаунт
        print("Пользователь не найден. Создание нового аккаунта.")

        display_name = input("Введите имя: ").strip()

        if not display_name:
            print("Имя не может быть пустым.")
            return

        password = getpass("Введите пароль: ")
        password_confirm = getpass("Повторите пароль: ")

        if len(password) < 6:
            print("Пароль должен содержать не менее 6 символов.")
            return

        if password != password_confirm:
            print("Пароли не совпадают.")
            return

        new_admin = User(
            email=email,
            password=hash_password(password),
            display_name=display_name,
            is_admin=True,
            is_blocked=False
        )

        session.add(new_admin)
        session.commit()

        print("Администратор успешно создан!")


if __name__ == "__main__":
    main()