from fastapi import BackgroundTasks
from typing import Annotated, Optional, List
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, File, UploadFile, Query

import uuid
import hashlib
import aiofiles
from pathlib import Path
from datetime import datetime

from backend.handlers import success_response
from backend.handlers.utils import logger, paginator_list

router = APIRouter(tags=['compress'])

CHUNK_SIZE = 1024 * 1024 * 5  # 每次读取 5MB
MAX_FILE_SIZE = 1024 * 1024 * 100  # 500MB
UPLOAD_DIR = Path("uploads")
TEMP_DIR = Path("temp")

# 允许的文件类型（按后缀过滤）
ALLOWED_FILE_TYPES = {
    ".zip", ".tar.gz", ".rar", ".tar", ".tar.bz", ".7z"
}


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
    for ext in ALLOWED_FILE_TYPES:
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
    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.iterdir():
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
    "/compress",
    summary='上传文件，添加压缩任务|支持大文件上传',
    description=f"支持压缩格式{', '.join(ALLOWED_FILE_TYPES)}",
    response_model=dict
)
async def add_compress_task(
        files: Annotated[Optional[List[UploadFile]], File(description="多个文件作为 UploadFile")] = None,
        background_tasks: BackgroundTasks = None
):
    """
    添加压缩任务 - 支持大文件上传
    """
    if not files:
        raise HTTPException(400, "没有上传任何文件")

    uploaded_files = []

    try:
        for file in files:
            # 验证文件
            validation_result = await validate_file(file)
            if "error" in validation_result:
                raise HTTPException(400, validation_result["error"])

            # 上传文件
            file_info = await upload_single_file(file)
            uploaded_files.append(file_info)

            # 添加后台处理任务
            if background_tasks:
                background_tasks.add_task(process_compress_task, file_info)

        return success_response({
            "files": uploaded_files,
            "task_id": str(uuid.uuid4()),
            "message": f"成功上传 {len(uploaded_files)} 个文件"
        })

    except HTTPException:
        raise
    except Exception as e:
        # 清理已上传的文件
        await cleanup_uploaded_files(uploaded_files)
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(500, f"文件上传失败: {str(e)}")


async def validate_file(file: UploadFile) -> dict:
    """验证单个文件"""
    # 判断是否为空文件
    if not file.filename or getattr(file, 'size', 0) == 0:
        return {"error": f"检测到空文件: {file.filename or '无文件名'}"}

    # 检查文件大小（预检查）
    if hasattr(file, 'size') and file.size > MAX_FILE_SIZE:
        return {
            "error": f"文件 {file.filename} 大小超过限制 {MAX_FILE_SIZE / (1024 * 1024):.2f} MB"
        }

    # 检查文件类型
    file_ext = get_file_extension(file.filename)
    if file_ext not in ALLOWED_FILE_TYPES:
        return {
            "error": f"不支持的文件类型: {file_ext} 仅支持 {', '.join(ALLOWED_FILE_TYPES)}"
        }

    return {"valid": True}


async def upload_single_file(file: UploadFile) -> dict:
    """上传单个文件 - 支持大文件"""
    # 生成唯一文件名
    if not UPLOAD_DIR.exists():
        UPLOAD_DIR.mkdir(exist_ok=True)
    if not TEMP_DIR.exists():
        TEMP_DIR.mkdir(exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    temp_path = TEMP_DIR / f"{unique_filename}.tmp"
    final_path = UPLOAD_DIR / unique_filename

    logger.info(f"[compress] 开始上传文件: {file.filename}")

    # 分块读取和写入文件
    md5_hash = hashlib.md5()
    total_size = 0

    try:
        async with aiofiles.open(temp_path, 'wb') as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_size += len(chunk)

                # 实时检查文件大小
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        400,
                        f"文件 {file.filename} 大小超过限制 {MAX_FILE_SIZE / (1024 * 1024):.2f} MB"
                    )

                # 更新MD5
                md5_hash.update(chunk)

                # 写入文件
                await out_file.write(chunk)

        # 移动临时文件到最终位置
        temp_path.rename(final_path)

        logger.info(f"[compress] 文件上传完成: {file.filename}, 大小: {total_size} bytes")

        return {
            "original_name": file.filename,
            "saved_name": unique_filename,
            "file_path": str(final_path),
            "size": f"{convert_bytes_to_mb(total_size)} MB",
            "md5": md5_hash.hexdigest(),
            "content_type": file.content_type,
            "uploaded_at": datetime.now().isoformat()
        }

    except Exception as e:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise e


async def process_compress_task(file_info: dict):
    """后台处理压缩任务"""
    try:
        logger.info(f"[compress] 开始处理文件: {file_info['original_name']}")
        # 这里添加实际的压缩处理逻辑
        # 例如：解压、重新压缩、格式转换等
        pass
    except Exception as e:
        logger.error(f"[compress] 处理文件失败 {file_info['original_name']}: {str(e)}")


async def cleanup_uploaded_files(uploaded_files: List[dict]):
    """
    清理已上传的文件
    :param uploaded_files: 已上传的文件列表
    :return:
    """
    for file_info in uploaded_files:
        try:
            file_path = Path(file_info.get("file_path", ""))
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.error(f"清理文件失败: {str(e)}")
