
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
