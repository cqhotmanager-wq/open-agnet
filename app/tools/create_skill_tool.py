from pathlib import Path
from typing import Any, Dict, List

from langchain.tools import BaseTool

from app.core.config import load_config


config = load_config()


class CreateSkillTool(BaseTool):
    name = "create_skill"
    description = "Create a new skill folder with SKILL.md, scripts, and references."

    def _run(self, **kwargs: Any) -> str:
        return self._create_skill(kwargs)

    async def _arun(self, **kwargs: Any) -> str:
        return self._create_skill(kwargs)

    def _create_skill(self, data: Dict[str, Any]) -> str:
        skill_name: str = data["skill_name"]
        description: str = data.get("description", "")
        scripts: List[Dict[str, str]] = data.get("scripts", [])
        references: List[Dict[str, str]] = data.get("references", [])

        root = Path(config.skill.root_path).resolve()
        skill_dir = root / skill_name
        scripts_dir = skill_dir / "scripts"
        refs_dir = skill_dir / "references"

        scripts_dir.mkdir(parents=True, exist_ok=True)
        refs_dir.mkdir(parents=True, exist_ok=True)

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            skill_md.write_text(
                f"# {skill_name}\n\n{description}\n",
                encoding="utf-8",
            )

        for s in scripts:
            (scripts_dir / s["filename"]).write_text(s.get("content", ""), encoding="utf-8")

        for r in references:
            (refs_dir / r["filename"]).write_text(r.get("content", ""), encoding="utf-8")

        return f"Skill '{skill_name}' created at {skill_dir}"

