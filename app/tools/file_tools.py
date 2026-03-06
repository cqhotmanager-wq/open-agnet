# 文件与目录操作工具：读文件、写文件、创建目录、列出目录（均限制在配置的根路径下）

from pathlib import Path
from typing import Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config import load_config
from app.core.skill_path import normalize_relative_to_skill_root

config = load_config()
# 允许操作的基础路径，防止越权访问
_BASE_PATH = Path(config.skill.root_path).resolve()


def _resolve_safe(path_str: str) -> Path:
    """将路径解析为绝对路径，并确保在 _BASE_PATH 之下。"""
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


class ReadFileInput(BaseModel):
    """读文件入参。"""
    file_path: str = Field(description="相对技能根路径或绝对路径（需在允许的根路径下）")
    encoding: str = Field(default="utf-8", description="文件编码")


class WriteFileInput(BaseModel):
    """写文件入参。"""
    file_path: str = Field(description="相对技能根路径或绝对路径")
    content: str = Field(description="要写入的文本内容")
    encoding: str = Field(default="utf-8", description="文件编码")


class CreateDirectoryInput(BaseModel):
    """创建目录入参。"""
    dir_path: str = Field(description="相对技能根路径或绝对路径，可多级如 a/b/c")
    exist_ok: bool = Field(default=True, description="已存在时是否不报错")


class ListDirectoryInput(BaseModel):
    """列出目录入参。"""
    dir_path: str = Field(default=".", description="相对技能根路径或绝对路径，默认为技能根")
    pattern: Optional[str] = Field(default=None, description="可选，glob 匹配如 *.md")


class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = "读取指定路径的文本文件内容。路径相对于技能根目录或为绝对路径（必须在允许范围内）。"
    args_schema: Type[ReadFileInput] = ReadFileInput

    def _run(self, file_path: str, encoding: str = "utf-8") -> str:
        p = _resolve_safe(file_path)
        if not p.is_file():
            return f"错误：路径不是文件或不存在 - {p}"
        return p.read_text(encoding=encoding)

    async def _arun(self, file_path: str, encoding: str = "utf-8") -> str:
        return self._run(file_path=file_path, encoding=encoding)


class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = "向指定路径写入文本内容，若目录不存在会先创建父目录。"
    args_schema: Type[WriteFileInput] = WriteFileInput

    def _run(self, file_path: str, content: str, encoding: str = "utf-8") -> str:
        p = _resolve_safe(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return f"已写入 {p}"

    async def _arun(self, file_path: str, content: str, encoding: str = "utf-8") -> str:
        return self._run(file_path=file_path, content=content, encoding=encoding)


class CreateDirectoryTool(BaseTool):
    name: str = "create_directory"
    description: str = "创建目录（可多级）。路径相对于技能根或为绝对路径。"
    args_schema: Type[CreateDirectoryInput] = CreateDirectoryInput

    def _run(self, dir_path: str, exist_ok: bool = True) -> str:
        p = _resolve_safe(dir_path)
        p.mkdir(parents=True, exist_ok=exist_ok)
        return f"已创建目录 {p}"

    async def _arun(self, dir_path: str, exist_ok: bool = True) -> str:
        return self._run(dir_path=dir_path, exist_ok=exist_ok)


class ListDirectoryTool(BaseTool):
    name: str = "list_directory"
    description: str = "列出指定目录下的子项（文件与目录）。可选 glob 过滤，如 *.md。"
    args_schema: Type[ListDirectoryInput] = ListDirectoryInput

    def _run(self, dir_path: str, pattern: Optional[str] = None) -> str:
        p = _resolve_safe(dir_path)
        if not p.is_dir():
            return f"错误：路径不是目录或不存在 - {p}"
        if pattern:
            items = sorted(p.glob(pattern))
        else:
            items = sorted(p.iterdir())
        names = [x.name for x in items]
        return "\n".join(names) if names else "(空)"

    async def _arun(self, dir_path: str, pattern: Optional[str] = None) -> str:
        return self._run(dir_path=dir_path, pattern=pattern)
