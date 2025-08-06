from fastapi import APIRouter
from backend.handlers import success_response

router = APIRouter(tags=['compress'])


# 获取支持格式
@router.get("/formats", summary='获取支持格式')
async def get_compress_formats():
    """
    获取支持的压缩格式
    支持的压缩格式包括 zip 和 tar.gz
    """
    return success_response(
        data={
            "formats": [
                {"name": "zip", "description": "ZIP 压缩格式"},
                {"name": "tar.gz", "description": "TAR.GZ 压缩格式"},
            ]
        }
    )
