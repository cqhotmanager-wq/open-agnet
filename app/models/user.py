"""
用户模型：对应表 users，用于登录鉴权与会话归属。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.db import Base


class User(Base):
    """用户表：主键 id、唯一用户名、bcrypt 密码哈希、创建时间。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

