# 技能列表 API（需登录）

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.user import User
from app.services.skill_service import SkillService


router = APIRouter(prefix="/skill", tags=["skill"])


@router.get("")
def list_skills(user: User = Depends(get_current_user)):
    """获取当前可用技能列表，需携带有效 JWT。"""
    _ = user
    service = SkillService()
    return {"skills": service.load_skills()}

