from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, Token, UserCreate, UserRead
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=UserRead)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.execute(select(User).where((User.email == payload.email) | (User.username == payload.username)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='User already exists')

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post('/login', response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail='Invalid credentials')

    token = create_access_token(str(user.id))
    return Token(access_token=token)
