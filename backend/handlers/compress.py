from typing import Annotated, Optional, List
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, BackgroundTasks, File, UploadFile, Query, Form

import uuid
import logging
from pathlib import Path
from datetime import datetime

from backend.config import settings
from backend.handlers import success_response
from backend.handlers.utils import paginator_list
from backend.handlers.core.zip_service import ZipService
from backend.handlers.core.file_service import FileService

router = APIRouter(tags=['compress'])

logger = logging.getLogger(__name__)


def convert_bytes_to_mb(size_in_bytes: int) -> float:
    """
    文件大小转换为 MB
    """
    return round(size_in_bytes / (1024 * 1024), 2)


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


# 获取支持格式
@router.get("/formats", summary='获取支持格式')
async def get_compress_formats():
    """
    获取支持的压缩格式
    支持的压缩格式包括 zip 和 tar.gz
    """
    formats = []
    for ext in settings.ALLOWED_FILE_TYPES:
        formats.append({
            "name": ext[1:],
            "description": f"{ext[1:].upper()} 压缩格式"
        })
    return success_response({"formats": formats})


# 添加文件列表查询接口
@router.get("/compress/files", summary="获取上传的文件列表")
async def get_uploaded_files(
        page: int = Query(1, description='page'),
        page_size: int = Query(10, description='page_size'),
):
    """
    获取已上传的文件列表
    :param page: 页码
    :param page_size: 每页数量
    :return: 文件列表
    """
    files = []
    if settings.UPLOAD_DIR.exists():
        for file_path in settings.UPLOAD_DIR.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": f"{convert_bytes_to_mb(stat.st_size)} MB",
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })

    count = len(files)
    data = paginator_list(files, page, page_size)
    return success_response({"files": data, "count": count})


@router.post(
    "/rezip",
    summary='重新压缩ZIP文件|支持大文件上传',
    description=f"支持压缩格式{', '.join(settings.ALLOWED_FILE_TYPES)}",
    response_model=dict
)
async def add_compress_task(
        files: Annotated[Optional[List[UploadFile]], File(description="多个文件作为 UploadFile")] = None,
        extract_password: Optional[str] = Form(None, description="解压密码"),
        compress_password: Optional[str] = Form(None, description="压缩密码"),
        compression_level: int = Form(6, ge=0, le=9, description="压缩级别 0-9"),
        background_tasks: BackgroundTasks = None
):
    """
    添加压缩任务 - 支持大文件上传
    :param background_tasks: 后台任务队列
    :param files:
    :param extract_password: 如果原文件有密码，需要提供extract_password
    :param compress_password: 如果需要密码保护，提供compress_password
    :param compression_level: 压缩级别 0-9, 0 表示无压缩，9 表示最大压缩
    """
    if not files:
        raise HTTPException(400, "没有上传任何文件")

    # 先验证整个文件队列
    try:
        validation_result = await FileService.validate_file_queue(files)
        if "error" in validation_result:
            raise HTTPException(400, validation_result["error"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件队列验证失败: {str(e)}")
        raise HTTPException(400, f"文件验证失败: {str(e)}")

    uploaded_files = []

    try:
        for file in files:
            file_info = await FileService.upload_single_file(file)
            uploaded_files.append(file_info)

            # 添加后台处理任务
            if background_tasks:
                background_tasks.add_task(
                    process_compress_task, file_info, extract_password, compress_password, compression_level
                )

        return success_response({
            "files": uploaded_files,
            "task_id": str(uuid.uuid4()),
            "message": f"成功上传 {len(uploaded_files)} 个文件"
        })

    except HTTPException:
        raise
    except Exception as e:
        # 清理已上传的文件
        await FileService.cleanup_uploaded_files(uploaded_files)
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(400, f"文件上传失败: {str(e)}")


async def process_compress_task(
        file_info: dict, extract_password: str, compress_password: str,
        compression_level: int):
    """
    后台处理压缩任务
    :param file_info: 文件信息
    :param extract_password: 解压密码
    :param compress_password: 压缩密码
    :param compression_level: 压缩级别
    """
    try:
        logger.debug(f"[compress] 开始处理文件: {file_info['original_name']}")

        # 原始ZIP文件路径
        original_zip_path: Path = settings.BASE_DIR / file_info['file_path']
        # 输出ZIP文件路径
        output_path: Path = Path("compressed") / f"{file_info['original_name']}.zip"
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        await ZipService.rezip_file(
            original_zip_path,
            output_path,
            extract_password,
            compress_password,
            compression_level
        )
        logger.info(f"[compress] 文件压缩成功: {output_path}")
    except Exception as e:
        logger.error(f"[compress] 处理文件失败 {file_info['original_name']}: {str(e)}")
