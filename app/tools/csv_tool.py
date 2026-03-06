# 加载 CSV 文件的工具

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


class LoadCsvInput(BaseModel):
    """加载 CSV 入参。"""
    file_path: str = Field(description="CSV 文件路径，相对技能根或绝对路径")
    encoding: str = Field(default="utf-8", description="文件编码")
    max_rows: int = Field(default=500, description="最多返回行数")
    delimiter: str = Field(default=",", description="分隔符，默认逗号")


class LoadCsvTool(BaseTool):
    name: str = "load_csv"
    description: str = "从指定路径加载 CSV 文件，将内容以表格文本形式返回。"
    args_schema: Type[LoadCsvInput] = LoadCsvInput

    def _run(
        self,
        file_path: str,
        encoding: str = "utf-8",
        max_rows: int = 500,
        delimiter: str = ",",
    ) -> str:
        try:
            import pandas as pd
        except ImportError:
            return "错误：未安装 pandas，请安装后重试。"

        p = _resolve_safe(file_path)
        if not p.is_file():
            return f"错误：文件不存在 - {p}"
        try:
            df = pd.read_csv(str(p), encoding=encoding, sep=delimiter, nrows=max_rows)
            return df.to_string(index=False)
        except Exception as e:
            return f"加载 CSV 失败: {e}"

    async def _arun(
        self,
        file_path: str,
        encoding: str = "utf-8",
        max_rows: int = 500,
        delimiter: str = ",",
    ) -> str:
        return self._run(
            file_path=file_path,
            encoding=encoding,
            max_rows=max_rows,
            delimiter=delimiter,
        )
