# 认证相关 API：注册、登录（均无需 token，公开接口）

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import create_access_token, get_auth_service, hash_password, verify_password
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    """注册请求体：用户名、密码。"""
    username: str
    password: str


class RegisterResponse(BaseModel):
    """注册成功返回提示。code 200 表示成功，500 表示失败。"""
    code: int = 200
    message: str = "注册成功"


class TokenResponse(BaseModel):
    """登录成功返回的 JWT 令牌。"""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """登录请求体：用户名、密码（JSON 提交）。"""
    username: str
    password: str


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    """用户注册：校验用户名是否已存在，创建用户并返回成功提示。不返回 token，需登录后获取。本接口无需 token 验证。"""
    existing = auth_service.get_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    auth_service.create_user(payload.username, hash_password(payload.password))
    return RegisterResponse()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    """用户登录：使用 JSON 提交用户名与密码，成功则返回 access_token。本接口无需 token 验证。"""
    user = auth_service.get_by_username(payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(access_token=token)

