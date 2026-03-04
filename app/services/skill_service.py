from pathlib import Path
from typing import Any, Dict, List

import json

from app.core.config import load_config


config = load_config()


class SkillService:
    def __init__(self) -> None:
        self.root = Path(config.skill.root_path).resolve()
        self.skill_json = Path(config.skill.skill_json_path).resolve()

    def load_skills(self) -> List[Dict[str, Any]]:
        if not self.skill_json.exists():
            return []
        data = json.loads(self.skill_json.read_text(encoding="utf-8"))
        return data.get("skills", [])

    def build_system_message_fragment(self) -> str:
        skills = self.load_skills()
        if not skills:
            return "当前没有可用技能。"
        lines: List[str] = ["你具备以下可用技能："]
        for s in skills:
            lines.append(f"- {s.get('name')}: {s.get('description')}")
        return "\n".join(lines)

