# 细粒度工具集合：文件/目录、Markdown、JSON、数据库、PDF/Word/Excel/CSV、网页抓取、搜索、HTML 解析

from typing import List

from langchain.tools import BaseTool

from app.tools.file_tools import (
    CreateDirectoryTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from app.tools.markdown_tool import ReadMarkdownTool
from app.tools.json_tools import ReadJsonTool, WriteJsonTool
from app.tools.db_tool import RunSqlTool
from app.tools.pdf_tool import LoadPdfTool
from app.tools.docx_tool import LoadDocxTool
from app.tools.excel_tool import LoadExcelTool
from app.tools.csv_tool import LoadCsvTool
from app.tools.web_fetch_tool import FetchWebPageTool
from app.tools.search_tool import SearchWebTool
from app.tools.html_tool import ParseHtmlTool


def get_all_tools() -> List[BaseTool]:
    """返回所有细粒度工具，供 Agent 使用。"""
    return [
        ReadFileTool(),
        WriteFileTool(),
        CreateDirectoryTool(),
        ListDirectoryTool(),
        ReadMarkdownTool(),
        ReadJsonTool(),
        WriteJsonTool(),
        RunSqlTool(),
        LoadPdfTool(),
        LoadDocxTool(),
        LoadExcelTool(),
        LoadCsvTool(),
        FetchWebPageTool(),
        SearchWebTool(),
        ParseHtmlTool(),
    ]


__all__ = [
    "get_all_tools",
    "ReadFileTool",
    "WriteFileTool",
    "CreateDirectoryTool",
    "ListDirectoryTool",
    "ReadMarkdownTool",
    "ReadJsonTool",
    "WriteJsonTool",
    "RunSqlTool",
    "LoadPdfTool",
    "LoadDocxTool",
    "LoadExcelTool",
    "LoadCsvTool",
    "FetchWebPageTool",
    "SearchWebTool",
    "ParseHtmlTool",
]
