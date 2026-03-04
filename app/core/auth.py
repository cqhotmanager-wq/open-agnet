from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import load_config
from app.core.db import get_db
from app.models.user import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
config = load_config()


class TokenData(BaseModel):
    user_id: int
    username: str


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: int, username: str, expires_minutes: Optional[int] = None) -> str:
    if expires_minutes is None:
        expires_minutes = config.jwt.expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(payload, config.jwt.secret, algorithm=config.jwt.algorithm)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, config.jwt.secret, algorithms=[config.jwt.algorithm])
        user_id: int = int(payload.get("user_id"))
        username: str = str(payload.get("username"))
        if user_id is None or username is None:
            raise ValueError("Invalid token payload")
        return TokenData(user_id=user_id, username=username)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    token_data = decode_token(token)
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

