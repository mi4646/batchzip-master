from typing import Annotated, Optional, List
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, File, UploadFile, Query, Form

import logging
from pathlib import Path
from datetime import datetime

from starlette.responses import FileResponse

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
        formats.append({"name": ext[1:]})
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
    if settings.COMPRESSED_DIR.exists():
        for file_path in settings.COMPRESSED_DIR.iterdir():
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
):
    """
    添加压缩任务 - 支持大文件上传
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

    results = []
    uploaded_files = []

    try:
        for file in files:
            try:
                file_info = await FileService.upload_single_file(file)
                uploaded_files.append(file_info)

                # 同步处理压缩
                logger.info(f"[compress] 开始处理文件: {file_info['original_name']}")

                original_zip_path: Path = settings.BASE_DIR / file_info['file_path']
                output_path: Path = settings.COMPRESSED_DIR / f"{file_info['original_name']}"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                await ZipService.rezip_file(
                    original_zip_path,
                    output_path,
                    extract_password,
                    compress_password,
                    compression_level
                )
                results.append({
                    "status": "success",
                    "output_path": str(output_path),
                    "file_name": file_info['original_name'],
                })

                logger.info(f"[compress] 文件压缩成功: {output_path}")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"[compress] 处理文件失败 {getattr(file, 'filename', 'unknown')}: {error_msg}")

                results.append({
                    "file_name": getattr(file, 'filename', 'unknown'),
                    "status": "failed",
                    "error": error_msg
                })

        # 构建最终响应
        successful_count = sum(1 for r in results if r["status"] == "success")
        failed_count = sum(1 for r in results if r["status"] == "failed")

        response_data = {
            "total_files": len(results),
            "successful": successful_count,
            "failed": failed_count,
            "results": results
        }

        # 清理所有上传的文件（无论成功失败）
        await FileService.cleanup_uploaded_files(uploaded_files)

        # 判断是否应该返回错误
        if len(results) > 0:
            if failed_count == len(results):
                # 所有文件都失败
                raise HTTPException(400, "所有文件处理失败")
            elif failed_count > 0:
                # 部分失败 - 仍然返回成功，但在消息中说明
                response_data["message"] = f"处理完成: {successful_count}个成功, {failed_count}个失败"
                return success_response(response_data)
            else:
                # 全部成功
                response_data["message"] = "所有文件处理成功"
                return success_response(response_data)
        else:
            # 没有文件需要处理
            raise HTTPException(400, "没有文件需要处理")

    except HTTPException:
        # 清理所有文件
        await FileService.cleanup_uploaded_files(uploaded_files)
        raise
    except Exception as e:
        # 系统错误，清理所有文件
        await FileService.cleanup_uploaded_files(uploaded_files)
        raise HTTPException(400, f"处理失败: {str(e)}")


# 下载压缩文件
@router.get("/compressed/download/{filename}", summary="下载压缩文件")
async def download_compressed_file(filename: str):
    """
    下载压缩文件
    :param filename: 文件名
    :return: 压缩文件
    """
    file_path = settings.COMPRESSED_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(file_path, filename=filename, media_type="application/zip")
