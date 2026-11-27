
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Преобразует пароль в безопасный хеш."""
    return password_hash.hash(password)


def verify_password(password: str, stored_password: str):
    """
    Проверяет пароль.

    Поддерживает:
    - новые пароли, сохранённые в виде Argon2-хеша;
    - старые пароли, сохранённые в открытом виде.

    Возвращает:
    (пароль верный, новый хеш или None).
    """
    if stored_password.startswith("$argon2"):
        valid, updated_hash = password_hash.verify_and_update(
            password,
            stored_password
        )
        return valid, updated_hash

    # Совместимость со старыми аккаунтами
    if password == stored_password:
        return True, hash_password(password)

    return False, None


def active_user_id(request, session):
    from models.users import User
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None
    if not user or user.is_blocked:
        request.session.clear()
        return None
    request.session["is_admin"] = user.is_admin
    request.session["user_name"] = user.display_name
    return user.id
