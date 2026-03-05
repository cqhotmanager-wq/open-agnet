# 加载 Word (.docx) 文档并提取文本的工具

from pathlib import Path
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import load_config

config = load_config()
_BASE_PATH = Path(config.skill.root_path).resolve()


def _resolve_safe(path_str: str) -> Path:
    p = (Path(path_str) if Path(path_str).is_absolute() else _BASE_PATH / path_str).resolve()
    try:
        p.relative_to(_BASE_PATH)
    except ValueError:
        raise ValueError(f"路径必须在 {_BASE_PATH} 之下")
    return p


class LoadDocxInput(BaseModel):
    """加载 Word 入参。"""
    file_path: str = Field(description=".docx 文件路径，相对技能根或绝对路径")
    max_chars: int = Field(default=50000, description="最多返回的字符数")


class LoadDocxTool(BaseTool):
    name: str = "load_docx"
    description: str = "从指定路径加载 Word (.docx) 文档并提取段落文本。"
    args_schema: Type[LoadDocxInput] = LoadDocxInput

    def _run(self, file_path: str, max_chars: int = 50000) -> str:
        try:
            from docx import Document
        except ImportError:
            return "错误：未安装 python-docx，请安装后重试。"

        p = _resolve_safe(file_path)
        if not p.is_file():
            return f"错误：文件不存在 - {p}"
        try:
            doc = Document(str(p))
            parts = [para.text for para in doc.paragraphs]
            text = "\n".join(parts)
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...(已截断)"
            return text
        except Exception as e:
            return f"加载 Word 文档失败: {e}"

    async def _arun(self, file_path: str, max_chars: int = 50000) -> str:
        return self._run(file_path=file_path, max_chars=max_chars)
