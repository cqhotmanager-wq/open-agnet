"""
会话服务：按用户获取或创建会话、按 user_id 列出所有会话、将会话置为未活跃。
会话周期由 session_uuid 唯一标识，与 chat 接口配合实现「每次访问可创建新会话或复用已有会话」。
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.session import Session as ChatSession
from app.models.user import User


class SessionService:
    """会话表（sessions）的增查与状态更新。"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(self, user: User, session_uuid: str | None = None) -> ChatSession:
        """若传入 session_uuid 且属于当前用户则复用，否则创建新会话（新 session_uuid）。"""
        if session_uuid:
            session = (
                self.db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_uuid == session_uuid)
                .first()
            )
            if session:
                return session

        new_session = ChatSession(user_id=user.id)
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        return new_session

    def list_sessions_by_user(self, user: User):
        """通过 user_id 查询该用户所有会话，按创建时间倒序。"""
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user.id)
            .order_by(desc(ChatSession.created_at))
            .all()
        )

    def deactivate_session(self, user: User, session_uuid: str) -> None:
        session = (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user.id, ChatSession.session_uuid == session_uuid)
            .first()
        )
        if session:
            session.is_active = False
            self.db.commit()

