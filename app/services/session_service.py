from sqlalchemy.orm import Session

from app.models.session import Session as ChatSession
from app.models.user import User


class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(self, user: User, session_uuid: str | None = None) -> ChatSession:
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

    def deactivate_session(self, user: User, session_uuid: str) -> None:
        session = (
            self.db.query(ChatSession)
            .filter(ChatSession.user_id == user.id, ChatSession.session_uuid == session_uuid)
            .first()
        )
        if session:
            session.is_active = False
            self.db.commit()

