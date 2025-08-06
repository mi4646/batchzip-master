from fastapi import APIRouter
from backend.handlers import success_response

router = APIRouter(tags=['health'])


@router.get("/healthz", summary='健康检查')
@router.get("/health", summary='健康检查')
async def health_check():
    """
    健康检查接口
    用于检查服务是否正常运行
    """
    return success_response(
        data={
            "status": "healthy",
            "message": "Service is running normally",
        }
    )


@router.get("/version", summary='版本检查')
async def version_check():
    """版本检查接口"""
    return success_response(
        data={
            "status": "healthy",
            "version": "v1.0.0",
            "message": "API v1 is running normally",
        }
    )
