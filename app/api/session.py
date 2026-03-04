from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.services.memory_service import MemoryService
from app.services.session_service import SessionService


router = APIRouter(prefix="/session", tags=["session"])


class SessionCreateResponse(BaseModel):
    session_uuid: str


@router.post("", response_model=SessionCreateResponse)
def create_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = SessionService(db)
    session = service.get_or_create_session(user)
    return SessionCreateResponse(session_uuid=session.session_uuid)


@router.delete("/{session_uuid}/memory")
def clear_session_memory(
    session_uuid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ = db  # currently unused, but kept for future extensions
    memory = MemoryService()
    memory.clear_session(user_id=user.id, session_uuid=session_uuid)
    return {"status": "ok"}

