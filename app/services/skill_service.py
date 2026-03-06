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

    def _resolve_location_path(self, location: str) -> Path:
        """将 skills.json 中的 location（如 ./skills/xxx/SKILL.md）解析为绝对路径。"""
        loc = location.strip().replace("\\", "/")
        if loc.startswith("./skills/"):
            rest = loc[len("./skills/") :]
        elif loc.startswith("skills/"):
            rest = loc[len("skills/") :]
        elif loc.startswith("./"):
            rest = loc[len("./") :]
        else:
            rest = loc
        rest = rest.lstrip("/")
        return (self.root / rest).resolve()

    def _read_skill_content(self, skill: Dict[str, Any]) -> str:
        """若技能有 location，则读取该文件内容并返回，否则返回空字符串。"""
        location = skill.get("location")
        if not location or not isinstance(location, str):
            return ""
        path = self._resolve_location_path(location)
        if not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    def build_system_message_fragment(self) -> str:
        skills = self.load_skills()
        if not skills:
            return "当前没有可用技能。"
        lines: List[str] = ["你具备以下可用技能（名称与描述见下），且每个技能附有完整说明文档内容，请按文档执行："]
        for s in skills:
            name = s.get("name", "")
            desc = s.get("description", "")
            location = s.get("location", "")
            lines.append(f"\n### 技能: {name}")
            lines.append(f"- 描述: {desc}")
            lines.append(f"- location: {location}")
            content = self._read_skill_content(s)
            if content:
                lines.append("文档内容 (SKILL.md):")
                lines.append("```")
                lines.append(content.strip())
                lines.append("```")
        return "\n".join(lines)

