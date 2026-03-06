# 会话相关 API：创建会话、清空会话记忆

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.session import Session as ChatSession
from app.models.user import User
from app.services.memory_manager import MemoryManager
from app.services.session_service import SessionService


router = APIRouter(prefix="/session", tags=["session"])


class SessionCreateResponse(BaseModel):
    """创建会话成功时返回的会话 UUID。"""
    session_uuid: str


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
    memory.clear_session(db, session_uuid)
    return {"status": "ok"}

