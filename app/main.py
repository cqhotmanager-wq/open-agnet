"""
应用入口：FastAPI 应用实例、全局异常处理、CORS、路由挂载。
启动时根据 ORM 模型创建数据库表（若不存在），并注册认证、会话、对话、技能等 API。
"""
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api import auth, chat, session, skill
from app.core.db import Base, engine
# 导入模型以便 Base.metadata.create_all 创建对应表
from app.models.chat_message import ChatMessage  # noqa: F401
from app.models.conversation_summary import ConversationSummary  # noqa: F401
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
    value_error_handler,
)


# 根据已注册的 ORM 模型自动创建缺失的表（MySQL/PostgreSQL）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Platform", version="0.1.0")

# 统一异常处理：按类型依次注册，最后用 Exception 兜底
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(skill.router, prefix="/api")


@app.get("/health")
def health():
    """健康检查接口，无需认证，用于负载均衡或监控探活。"""
    return {"status": "ok"}

