"""
对话 API：发送用户消息，由 Agent 结合上下文（最近历史、摘要、向量检索）调用 LLM 与工具后返回回复。
需登录；会话周期由 session_uuid 标识，不传则创建新会话。
"""
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
    """
    发送一条消息。每个会话周期内 session_uuid 唯一且整轮对话一致。
    - 未传 session_uuid 或传空：创建新会话周期，返回新 session_uuid，后续请求请携带该 id 以保持同一上下文。
    - 传 session_uuid：复用该会话（须属于当前用户），在同一上下文中继续对话。
    """
    session_service = SessionService(db)
    session = session_service.get_or_create_session(user, payload.session_uuid)
    agent_service = AgentService()
    answer = agent_service.chat(
        user=user,
        session_uuid=session.session_uuid,
        message=payload.message,
        db=db,
    )
    return ChatResponse(session_uuid=session.session_uuid, answer=answer)

