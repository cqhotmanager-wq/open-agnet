# 抓取指定网页内容的工具

from typing import Optional, Type

import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class FetchWebPageInput(BaseModel):
    """抓取网页入参。"""
    url: str = Field(description="要抓取的网页 URL，需包含 http(s)://")
    timeout: int = Field(default=15, description="请求超时秒数")
    encoding: Optional[str] = Field(default=None, description="响应编码，不填则自动检测")


class FetchWebPageTool(BaseTool):
    name: str = "fetch_web_page"
    description: str = "根据 URL 抓取网页的 HTML 文本内容。用于获取指定网页的原始内容。"
    args_schema: Type[FetchWebPageInput] = FetchWebPageInput

    def _run(self, url: str, timeout: int = 15, encoding: Optional[str] = None) -> str:
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            if encoding:
                resp.encoding = encoding
            return resp.text
        except requests.RequestException as e:
            return f"请求失败: {e}"

    async def _arun(
        self,
        url: str,
        timeout: int = 15,
        encoding: Optional[str] = None,
    ) -> str:
        return self._run(url=url, timeout=timeout, encoding=encoding)
