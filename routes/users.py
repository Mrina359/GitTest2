from fastapi import APIRouter, HTTPException
from models.users import User, UserSignIn
from database.connection import Database

user_router = APIRouter(tags=["User"])
user_database = Database(User)

@user_router.post("/signup")
async def sign_user_up(user: User):
    user_exist = await User.find_one(User.email == user.email)
    if user_exist:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    await user_database.save(user)
    return {"message": "Пользователь успешно зарегистрирован в системе Ишмухаметовой М.Р."}

@user_router.post("/signin")
async def sign_user_in(user: UserSignIn):
    user_exist = await User.find_one(User.email == user.email)
    if not user_exist or user_exist.password != user.password:
        raise HTTPException(status_code=401, detail="Неверный пароль или email")
    return {"message": "Успешный вход в систему Ишмухаметовой М.Р."}