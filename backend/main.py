import uvicorn
from fastapi import FastAPI, status
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException, RequestValidationError

from backend.routes import routers
from backend.config import settings as config
from backend.handlers.utils import (
    logger,
    logging,
    setup_logging,
    init_redis_client,
)

from backend.handlers.utils.exception import (
    APIError,
    not_found_handler,
    api_error_handler,
    http_error_handler,
    exception_error_handler,
    validation_error_handler,
)


def setup_routes(application):
    """
    设置所有路由
    :param application: FastAPI 应用实例
    """
    for router, prefix in routers:
        application.include_router(router, prefix=prefix)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 初始化Redis...")

    # 初始化 Redis
    redis_client = await init_redis_client(raise_on_failure=True)
    app.state.redis = redis_client

    yield
    # 关闭 Redis
    logger.info("🛑 正在关闭 Redis 连接...")
    await redis_client.aclose()
    logger.info("👋 应用已安全关闭")


def get_application() -> FastAPI:
    application = FastAPI(
        title=config.PROJECT_NAME,
        debug=config.DEBUG,
        version=config.VERSION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        contact={
            "name": "技术支持",
            "url": "https://github.com/mi4646/batchzip-master",
            "email": "support@example.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://mit-license.org/"
        }
    )

    # CORS 中间件配置
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=config.ALLOWED_METHODS,
        allow_headers=config.ALLOWED_HEADERS,
    )

    # 404 专门处理器
    application.add_exception_handler(status.HTTP_404_NOT_FOUND, not_found_handler)
    # HTTPException 处理器
    application.add_exception_handler(HTTPException, http_error_handler)
    # RequestValidationError 处理器
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(APIError, api_error_handler)
    # 全局异常处理器
    application.add_exception_handler(Exception, exception_error_handler)

    # 配置路由
    setup_routes(application)
    return application


def get_uvicorn_config() -> dict:
    """
    从 Config 中提取关键参数
    """

    # 默认日志等级（根据 debug 设置）
    log_level = logging.DEBUG if config.DEBUG else logging.INFO
    setup_logging(log_level)

    uvicorn_config = {
        "host": config.HOST,
        "port": config.PORT,
        "log_level": log_level,
    }

    return uvicorn_config


app = get_application()

if __name__ == '__main__':
    # uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    uvicorn.run(app, **get_uvicorn_config())
