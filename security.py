from pwdlib import PasswordHash
from fastapi import Request, HTTPException
from sqlmodel import Session

from models.users import User


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Преобразует пароль в безопасный хеш."""
    return password_hash.hash(password)


def verify_password(password: str, stored_password: str):
    """Проверяет пароль пользователя."""

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


def active_user_id(request: Request, session: Session):
    """Возвращает ID активного пользователя."""

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = session.get(User, user_id)

    if not user or user.is_blocked:
        request.session.clear()
        return None

    # Обновляем информацию о пользователе в сессии
    request.session["user_name"] = user.display_name
    request.session["is_admin"] = user.is_admin

    return user.id