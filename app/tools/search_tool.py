# 调用搜索引擎获取搜索结果的工具

from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class SearchWebInput(BaseModel):
    """网页搜索入参。"""
    query: str = Field(description="搜索关键词或问句")
    max_results: int = Field(default=5, description="最多返回几条结果")


class SearchWebTool(BaseTool):
    name: str = "search_web"
    description: str = "使用搜索引擎根据关键词获取搜索结果（标题、链接、摘要）。适用于查实时信息。"
    args_schema: Type[SearchWebInput] = SearchWebInput

    def _run(self, query: str, max_results: int = 5) -> str:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "错误：未安装 duckduckgo-search，请安装后重试。"

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "未找到相关结果。"
            lines = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                href = r.get("href", "")
                body = r.get("body", "")
                lines.append(f"{i}. {title}\n   {href}\n   {body}")
            return "\n\n".join(lines)
        except Exception as e:
            return f"搜索失败: {e}"

    async def _arun(self, query: str, max_results: int = 5) -> str:
        return self._run(query=query, max_results=max_results)
