from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import RequestValidationError

from backend.handlers.utils.logs import logger
import traceback


class APIError(Exception):
    """
    API错误基类
    :param status_code: 状态码
    :param detail: 错误详情
    :param error_code: 错误码
    """

    def __init__(self, status_code: int = 400, detail: str = "Bad Request", error_code: str = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or "API_ERROR"
        super().__init__(self.detail)


class AuthenticationError(APIError):
    """
    认证错误
    :param detail: 错误详情
    :param error_code: 错误码
    """

    def __init__(self, detail: str = "Authentication failed", error_code: str = "authentication_error"):
        super().__init__(
            status_code=401, detail=detail, error_code=error_code
        )


async def not_found_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
    """
    404 专门处理
    :param request: 请求对象
    :param exc: 异常对象
    :return: ORJSONResponse
    """
    logger.error(f"404 Handler triggered {exc.status_code} | Path: {request.url.path}")
    response_data = {
        'code': 404,
        'error': exc.detail,
        "message": "资源未找到 | Not Found. 请检查API文档以获取可用端点.",
        'docs_url': str(request.url.replace(path="/api/docs"))
    }
    return ORJSONResponse(content=response_data, status_code=404)


async def http_error_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
    """
    http异常处理
    :param request: 请求对象
    :param exc: 异常对象
    :return: ORJSONResponse
    """
    logger.error(f"HTTPException {exc.status_code} -> {exc.detail} | Path: {request.url.path}")
    response_data = {
        'code': exc.status_code,
        'message': '错误 | Fail',
        'error': exc.detail
    }
    return ORJSONResponse(response_data)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
    """
    参数验证异常处理
    :param request: 请求对象
    :param exc: 异常对象
    :return: ORJSONResponse
    """
    logger.error(f"ValidationError -> {exc.errors()} | Path: {request.url.path}")
    response_data = {
        'code': 422, 'message': '参数错误 | Fail',
        'error': exc.errors()[0]['msg'] if exc.errors() else '',
        'error_info': exc.errors(),
        "body": exc.body,
    }
    return ORJSONResponse(response_data)


async def api_error_handler(request: Request, exc: APIError) -> ORJSONResponse:
    """
    处理API错误
    :param request: 请求对象
    :param exc: 异常对象
    :return: ORJSONResponse
    """
    logger.error(f"APIError -> {exc.detail} | Path: {request.url.path} | Error Code: {exc.error_code}")
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": "API 错误 | Fail",
            "error": exc.detail,
            "error_info": exc.error_code,
        }
    )


async def exception_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """
    处理通用异常
    :param request: 请求对象
    :param exc: 异常对象
    :return: ORJSONResponse
    """
    #  FastAPI 的 debug 模式下（debug=True），某些错误会直接由 Starlette 处理
    logger.exception(f"Unhandled Exception -> {repr(exc)} | Path: {request.url.path}")
    logger.error("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

    return ORJSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器开小差了",
            "error": "Internal Server Error"
        }
    )


__all__ = [
    'APIError',
    'not_found_handler',
    'api_error_handler',
    'AuthenticationError',
    'http_error_handler',
    'validation_error_handler',
    'exception_error_handler',
]
