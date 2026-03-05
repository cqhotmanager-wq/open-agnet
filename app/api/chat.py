# 对话 API：发送消息并获取 Agent 回复

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.llm_config import ChatRequest, ChatResponse
from app.models.user import User
from app.services.agent_service import AgentService
from app.services.session_service import SessionService


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """发送一条消息，按 session_uuid 获取或创建会话，调用 Agent 并返回回复。"""
    session_service = SessionService(db)
    session = session_service.get_or_create_session(user, payload.session_uuid)
    agent_service = AgentService()
    answer = agent_service.chat(user=user, session_uuid=session.session_uuid, message=payload.message)
    return ChatResponse(session_uuid=session.session_uuid, answer=answer)

