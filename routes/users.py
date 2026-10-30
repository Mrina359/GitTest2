from fastapi import APIRouter, HTTPException, status
from models.users import User, NewUser, UserSignIn

user_router = APIRouter(tags=["User"])

# «База данных» в памяти
users = {}


@user_router.post("/signup")
async def sign_new_user(data: NewUser) -> dict:
    if data.email in users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует в базе Ишмухаметовой М.Р."
        )
    users[data.email] = data
    return {"message": "Пользователь успешно зарегистрирован в системе Ишмухаметовой М.Р."}


@user_router.post("/signin")
async def sign_user_in(user: UserSignIn) -> dict:
    if user.email not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден в системе Ишмухаметовой М.Р."
        )
    if users[user.email].password != user.password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный пароль"
        )
    return {"message": "Успешный вход в систему Ишмухаметовой М.Р."}