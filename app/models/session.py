"""
会话模型：每个用户可拥有多轮会话，每轮会话有唯一 session_uuid。
通过 user_id 可查询该用户下所有会话；user_id + session_uuid 唯一标识一轮对话周期。
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.db import Base


class Session(Base):
    """会话表：关联用户、全局唯一的 session_uuid、是否活跃、创建时间。"""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_uuid = Column(String(64), unique=True, index=True, default=lambda: str(uuid4()))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", backref="sessions")

