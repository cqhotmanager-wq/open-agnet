# 统一异常与错误响应格式

from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ---------- 统一错误响应体 ----------


class ErrorResponse(BaseModel):
    """统一错误响应结构。code 为数字：200 成功，400/401/404/422/500 等为失败。"""
    success: bool = False
    code: int = 500
    message: str = ""
    detail: Optional[Any] = None


def error_response(
    status_code: int,
    message: str,
    detail: Optional[Any] = None,
    *,
    code: Optional[int] = None,
) -> JSONResponse:
    """生成统一格式的 JSON 错误响应。body.code 与 HTTP 状态码一致（如 400、500）。"""
    body = ErrorResponse(
        code=code if code is not None else status_code,
        message=message,
        detail=detail,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
    )


# ---------- 自定义业务异常（可选，便于在业务层 raise） ----------


class AppException(Exception):
    """业务异常基类，可携带 HTTP 状态码与错误码。"""
    def __init__(
        self,
        message: str = "业务处理失败",
        status_code: int = 400,
        code: str = "BAD_REQUEST",
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppException):
    """资源不存在。"""
    def __init__(self, message: str = "资源不存在", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=404,
            code="NOT_FOUND",
            detail=detail,
        )


class UnauthorizedError(AppException):
    """未授权 / token 无效。"""
    def __init__(self, message: str = "未授权或凭证无效", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=401,
            code="UNAUTHORIZED",
            detail=detail,
        )


# ---------- 全局异常处理器（在 main 中注册） ----------


async def http_exception_handler(request: Request, exc) -> JSONResponse:
    """处理 FastAPI HTTPException，转为统一错误格式。body.code 为 HTTP 状态码。"""
    status_code = exc.status_code
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
    else:
        message = str(detail) if detail else "请求处理失败"
    return error_response(status_code, message=message, detail=detail if isinstance(detail, dict) else None)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求体验证错误（422），返回可读的字段错误列表。"""
    errors = exc.errors()
    messages = []
    for e in errors:
        loc = ".".join(str(x) for x in e.get("loc", []) if x != "body")
        msg = e.get("msg", "参数错误")
        messages.append(f"{loc}: {msg}" if loc else msg)
    message = "请求参数校验失败" if len(messages) > 1 else (messages[0] if messages else "请求参数错误")
    return error_response(422, message=message, detail=errors)


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """处理 ValueError（如工具层路径越权、参数错误）。"""
    return error_response(400, message=str(exc))


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理自定义业务异常。"""
    return error_response(
        exc.status_code,
        message=exc.message,
        detail=exc.detail,
    )


async def sqlalchemy_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理数据库相关异常，避免把内部错误信息暴露给前端。"""
    return error_response(500, message="数据库操作失败，请稍后重试")


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：未捕获的异常，统一返回 500。"""
    return error_response(500, message="服务器内部错误，请稍后重试")
