# 加载 PDF 并提取文本的工具

from pathlib import Path
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from pypdf import PdfReader

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


class LoadPdfInput(BaseModel):
    """加载 PDF 入参。"""
    file_path: str = Field(description="PDF 文件路径，相对技能根或绝对路径")
    max_chars: int = Field(default=50000, description="最多返回的字符数，避免过长")


class LoadPdfTool(BaseTool):
    name: str = "load_pdf"
    description: str = "从指定路径加载 PDF 文件并提取文本内容返回。"
    args_schema: Type[LoadPdfInput] = LoadPdfInput

    def _run(self, file_path: str, max_chars: int = 50000) -> str:
        p = _resolve_safe(file_path)
        if not p.is_file():
            return f"错误：文件不存在 - {p}"
        try:
            reader = PdfReader(str(p))
            parts = []
            total = 0
            for page in reader.pages:
                text = page.extract_text() or ""
                if total + len(text) > max_chars:
                    parts.append(text[: max_chars - total])
                    total = max_chars
                    break
                parts.append(text)
                total += len(text)
            out = "\n".join(parts)
            if total >= max_chars:
                out += "\n...(已截断)"
            return out
        except Exception as e:
            return f"加载 PDF 失败: {e}"

    async def _arun(self, file_path: str, max_chars: int = 50000) -> str:
        return self._run(file_path=file_path, max_chars=max_chars)
