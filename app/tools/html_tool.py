# 用于解析 HTML 的工具（从字符串或 URL 提取可读文本或结构）

from typing import Optional, Type

import requests
from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class ParseHtmlInput(BaseModel):
    """解析 HTML 入参。"""
    source: str = Field(
        description="HTML 字符串，或以 http:///https:// 开头的 URL（将先抓取再解析）",
    )
    extract_text_only: bool = Field(
        default=True,
        description="为 True 时只返回纯文本；为 False 时返回主要标签结构摘要",
    )
    timeout: int = Field(default=15, description="当 source 为 URL 时的请求超时秒数")


class ParseHtmlTool(BaseTool):
    name: str = "parse_html"
    description: str = "解析 HTML：若传入 URL 则先抓取再解析；可提取纯文本或标签结构，便于后续分析。"
    args_schema: Type[ParseHtmlInput] = ParseHtmlInput

    def _run(
        self,
        source: str,
        extract_text_only: bool = True,
        timeout: int = 15,
    ) -> str:
        html: str
        if source.strip().startswith(("http://", "https://")):
            try:
                resp = requests.get(source.strip(), timeout=timeout)
                resp.raise_for_status()
                html = resp.text
            except requests.RequestException as e:
                return f"请求 URL 失败: {e}"
        else:
            html = source

        try:
            soup = BeautifulSoup(html, "html.parser")
            # 去掉脚本和样式
            for tag in soup(["script", "style"]):
                tag.decompose()
            if extract_text_only:
                text = soup.get_text(separator="\n", strip=True)
                return text[:50000] if len(text) > 50000 else text
            # 简单结构摘要：主要块级标签及其 class/id
            parts = []
            for tag in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "table"]):
                name = tag.name
                attrs = " ".join(f'{k}="{v}"' for k, v in tag.attrs.items() if k in ("id", "class"))
                content = (tag.get_text(strip=True) or "")[:200]
                parts.append(f"<{name} {attrs}> {content}")
            return "\n".join(parts[:500]) if parts else soup.get_text(separator="\n", strip=True)[:50000]
        except Exception as e:
            return f"解析 HTML 失败: {e}"

    async def _arun(
        self,
        source: str,
        extract_text_only: bool = True,
        timeout: int = 15,
    ) -> str:
        return self._run(
            source=source,
            extract_text_only=extract_text_only,
            timeout=timeout,
        )
