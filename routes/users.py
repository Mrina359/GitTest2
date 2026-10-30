from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from database.connection import get_session
from models.users import User, NewUser, UserSignIn

user_router = APIRouter(tags=["User"])

@user_router.post("/signup")
async def sign_new_user(data: NewUser, session: Session = Depends(get_session)) -> dict:
    # Ищем пользователя в БД по email
    user_exist = session.exec(select(User).where(User.email == data.email)).first()
    
    if user_exist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует в базе Ишмухаметовой М.Р."
        )
    
    # Создаем нового пользователя и сохраняем в БД
    new_user = User(email=data.email, password=data.password)
    session.add(new_user)
    session.commit()
    
    return {"message": "Пользователь успешно зарегистрирован в системе Ишмухаметовой М.Р."}


@user_router.post("/signin")
async def sign_user_in(user: UserSignIn, session: Session = Depends(get_session)) -> dict:
    # Ищем пользователя в БД
    user_exist = session.exec(select(User).where(User.email == user.email)).first()
    
    if not user_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден в системе Ишмухаметовой М.Р."
        )
    
    if user_exist.password != user.password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный пароль. Доступ к системе Ишмухаметовой М.Р. запрещен"
        )
        
    return {"message": "Успешный вход в систему Ишмухаметовой М.Р."}