from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.user import User
from app.services.skill_service import SkillService


router = APIRouter(prefix="/skill", tags=["skill"])


@router.get("")
def list_skills(user: User = Depends(get_current_user)):
    _ = user
    service = SkillService()
    return {"skills": service.load_skills()}

