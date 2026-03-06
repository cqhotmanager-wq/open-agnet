"""
对话 API 的请求/响应模型：Chat 接口入参与返回结构。
"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """发送消息请求：message 必填；session_uuid 可选，不传则创建新会话周期。"""
    session_uuid: str | None = None
    message: str


class ChatResponse(BaseModel):
    """对话响应：本轮使用的 session_uuid 与 Agent 回复内容。"""
    session_uuid: str
    answer: str

