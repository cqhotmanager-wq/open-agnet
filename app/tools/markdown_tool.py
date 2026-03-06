# 读取并加载 Markdown 文档的工具

from pathlib import Path
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import load_config
from app.core.skill_path import normalize_relative_to_skill_root

config = load_config()
_BASE_PATH = Path(config.skill.root_path).resolve()


def _resolve_safe(path_str: str) -> Path:
    if Path(path_str).is_absolute():
        p = Path(path_str).resolve()
    else:
        rel = normalize_relative_to_skill_root(path_str)
        p = (_BASE_PATH / rel).resolve()
    try:
        p.relative_to(_BASE_PATH)
    except ValueError:
        raise ValueError(f"路径必须在 {_BASE_PATH} 之下")
    return p


class ReadMarkdownInput(BaseModel):
    """读取 Markdown 入参。"""
    file_path: str = Field(description=".md 文件路径，相对技能根或绝对路径")
    encoding: str = Field(default="utf-8", description="文件编码")


class ReadMarkdownTool(BaseTool):
    name: str = "read_markdown"
    description: str = "读取并返回 Markdown 文档的原始文本内容，适用于 .md 文件。"
    args_schema: Type[ReadMarkdownInput] = ReadMarkdownInput

    def _run(self, file_path: str, encoding: str = "utf-8") -> str:
        p = _resolve_safe(file_path)
        if not p.is_file():
            return f"错误：文件不存在或不是文件 - {p}"
        return p.read_text(encoding=encoding)

    async def _arun(self, file_path: str, encoding: str = "utf-8") -> str:
        return self._run(file_path=file_path, encoding=encoding)
