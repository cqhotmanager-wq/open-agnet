"""
会话 API：创建会话、按当前用户查询其所有会话列表、清空指定会话的记忆（SQL + Milvus）。
所有接口需登录；通过 user_id（从 JWT 解析）限定仅操作当前用户数据。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.session import Session as ChatSession
from app.models.user import User
from app.manager.memory_manager import MemoryManager
from app.services.session_service import SessionService


router = APIRouter(prefix="/session", tags=["session"])


class SessionCreateResponse(BaseModel):
    """创建会话成功时返回的会话 UUID。"""
    session_uuid: str


class SessionItem(BaseModel):
    """单条会话（供列表返回）。"""
    session_uuid: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """通过 user_id 查询到的用户所有会话。"""
    sessions: list[SessionItem]


@router.get("", response_model=SessionListResponse)
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """通过当前用户 id 查询该用户所有会话，按创建时间倒序。"""
    service = SessionService(db)
    sessions = service.list_sessions_by_user(user)
    return SessionListResponse(
        sessions=[
            SessionItem(
                session_uuid=s.session_uuid,
                is_active=s.is_active,
                created_at=s.created_at,
            )
            for s in sessions
        ]
    )


@router.post("", response_model=SessionCreateResponse)
def create_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建或复用会话，返回 session_uuid。"""
    service = SessionService(db)
    session = service.get_or_create_session(user)
    return SessionCreateResponse(session_uuid=session.session_uuid)


@router.delete("/{session_uuid}/memory")
def clear_session_memory(
    session_uuid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """清空指定会话的记忆（SQL 聊天/摘要 + Milvus 向量），仅限当前用户。"""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id, ChatSession.session_uuid == session_uuid)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    memory = MemoryManager()
    memory.clear_session(db, user_id=user.id, session_uuid=session_uuid)
    return {"status": "ok"}

