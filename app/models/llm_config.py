from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_uuid: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_uuid: str
    answer: str

