from pathlib import Path
from typing import Any, Dict, List

import json
from langchain.tools import BaseTool

from app.core.config import load_config


config = load_config()


class SkillTool(BaseTool):
    name = "skill_router"
    description = "Use configured skills; returns descriptions and locations for the agent."

    def _run(self, **kwargs: Any) -> str:
        return json.dumps(self._load_skills(), ensure_ascii=False)

    async def _arun(self, **kwargs: Any) -> str:
        return json.dumps(self._load_skills(), ensure_ascii=False)

    def _load_skills(self) -> Dict[str, Any]:
        skill_json = Path(config.skill.skill_json_path).resolve()
        if not skill_json.exists():
            return {"skills": []}
        data = json.loads(skill_json.read_text(encoding="utf-8"))
        return data

