# 加载 Excel 文件并提取表格内容（文本形式）的工具

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


class LoadExcelInput(BaseModel):
    """加载 Excel 入参。"""
    file_path: str = Field(description=".xlsx/.xls 文件路径，相对技能根或绝对路径")
    sheet_name: str = Field(default="", description="工作表名称，空则取第一个表")
    max_rows: int = Field(default=500, description="最多返回行数，避免过长")


class LoadExcelTool(BaseTool):
    name: str = "load_excel"
    description: str = "从指定路径加载 Excel 文件，将指定工作表转为文本表格返回。"
    args_schema: Type[LoadExcelInput] = LoadExcelInput

    def _run(self, file_path: str, sheet_name: str = "", max_rows: int = 500) -> str:
        try:
            import openpyxl
        except ImportError:
            return "错误：未安装 openpyxl，请安装后重试。"

        p = _resolve_safe(file_path)
        if not p.is_file():
            return f"错误：文件不存在 - {p}"
        try:
            wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
            if sheet_name:
                ws = wb[sheet_name]
            else:
                ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if not rows:
                return "表为空。"
            head = rows[0]
            data = rows[1 : max_rows + 1]
            lines = ["\t".join(str(c) if c is not None else "" for c in head)]
            for row in data:
                lines.append("\t".join(str(c) if c is not None else "" for c in row))
            if len(rows) > max_rows + 1:
                lines.append(f"...(共 {len(rows)} 行，已截断)")
            return "\n".join(lines)
        except Exception as e:
            return f"加载 Excel 失败: {e}"

    async def _arun(
        self,
        file_path: str,
        sheet_name: str = "",
        max_rows: int = 500,
    ) -> str:
        return self._run(file_path=file_path, sheet_name=sheet_name, max_rows=max_rows)
