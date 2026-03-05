# JSON 读写工具

import json
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


class ReadJsonInput(BaseModel):
    """读 JSON 入参。"""
    file_path: str = Field(description="JSON 文件路径，相对技能根或绝对路径")
    encoding: str = Field(default="utf-8", description="文件编码")


class WriteJsonInput(BaseModel):
    """写 JSON 入参。"""
    file_path: str = Field(description="JSON 文件路径")
    content: str = Field(description="JSON 字符串或可序列化的结构描述，将按 JSON 解析后写入")
    encoding: str = Field(default="utf-8", description="文件编码")
    indent: int = Field(default=2, description="缩进空格数，便于阅读")


class ReadJsonTool(BaseTool):
    name: str = "read_json"
    description: str = "从指定路径读取 JSON 文件并返回解析后的内容（字符串形式）。"
    args_schema: Type[ReadJsonInput] = ReadJsonInput

    def _run(self, file_path: str, encoding: str = "utf-8") -> str:
        p = _resolve_safe(file_path)
        if not p.is_file():
            return f"错误：文件不存在 - {p}"
        try:
            data = json.loads(p.read_text(encoding=encoding))
            return json.dumps(data, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            return f"JSON 解析错误: {e}"

    async def _arun(self, file_path: str, encoding: str = "utf-8") -> str:
        return self._run(file_path=file_path, encoding=encoding)


class WriteJsonTool(BaseTool):
    name: str = "write_json"
    description: str = "将 JSON 字符串写入指定路径。content 需为合法 JSON 字符串。"
    args_schema: Type[WriteJsonInput] = WriteJsonInput

    def _run(self, file_path: str, content: str, encoding: str = "utf-8", indent: int = 2) -> str:
        p = _resolve_safe(file_path)
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return f"JSON 格式错误: {e}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding=encoding)
        return f"已写入 {p}"

    async def _arun(
        self,
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        indent: int = 2,
    ) -> str:
        return self._run(file_path=file_path, content=content, encoding=encoding, indent=indent)
