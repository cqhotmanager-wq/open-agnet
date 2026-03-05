# 认证核心：密码哈希、JWT 签发/解析、当前用户依赖

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import load_config
from app.core.db import get_db
from app.models.user import User
from app.services.auth_service import AuthService


# 密码加密上下文（bcrypt）；bcrypt 仅支持最多 72 字节，超出需截断
BCRYPT_MAX_PASSWORD_BYTES = 72


def _truncate_password_for_bcrypt(password: str) -> str:
    """将密码截断为最多 72 字节（UTF-8），避免 bcrypt 报错。"""
    enc = password.encode("utf-8")
    if len(enc) <= BCRYPT_MAX_PASSWORD_BYTES:
        return password
    return enc[:BCRYPT_MAX_PASSWORD_BYTES].decode("utf-8", errors="ignore")


# OAuth2 Bearer 方案，token 从 /api/auth/login 获取
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
config = load_config()


class TokenData(BaseModel):
    """JWT 解析后的用户标识。"""
    user_id: int
    username: str


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否一致。密码会按 bcrypt 限制截断至 72 字节。"""
    pwd = _truncate_password_for_bcrypt(plain_password).encode("utf-8")
    expected = password_hash.encode("utf-8") if isinstance(password_hash, str) else password_hash
    return bcrypt.checkpw(pwd, expected)


def hash_password(password: str) -> str:
    """对密码做 bcrypt 哈希，用于存储。超过 72 字节的密码会先截断再哈希。"""
    pwd = _truncate_password_for_bcrypt(password).encode("utf-8")
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("ascii")


def create_access_token(user_id: int, username: str, expires_minutes: Optional[int] = None) -> str:
    """生成 JWT access_token，过期时间可指定或使用配置默认值。"""
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
    """解析 JWT，失败则抛出 401。"""
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


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """依赖注入：根据当前请求的 db 会话返回 AuthService。"""
    return AuthService(db)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """依赖注入：从 Bearer token 解析用户并查库，未找到或 token 无效则 401。"""
    token_data = decode_token(token)
    user = auth_service.get_by_id(token_data.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

