from typing import List, Dict
from fastapi import UploadFile, HTTPException

import uuid
import hashlib
import logging
import aiofiles
from pathlib import Path
from datetime import datetime

from backend.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """
    文件处理服务类
    """

    @staticmethod
    async def validate_file_queue(files: List[UploadFile]) -> dict:
        """
        验证整个文件队列
        :param files: 文件列表
        :return: 验证结果
        """
        if not files:
            return {"error": "文件列表为空"}

        file_names = set()

        for file in files:
            # 检查文件名重复
            if file.filename in file_names:
                return {"error": f"文件名重复: {file.filename}"}
            file_names.add(file.filename)

            # 检查单个文件
            file_validation = await FileService.validate_single_file(file)
            if "error" in file_validation:
                return file_validation

        # 检查总文件数量
        if len(files) > settings.MAX_FILES_PER_REQUEST:
            return {"error": f"文件数量超过限制 {settings.MAX_FILES_PER_REQUEST} 个"}

        return {"success": True, "total_files": len(files)}

    @staticmethod
    async def validate_single_file(file: UploadFile) -> dict:
        """
        验证单个文件
        :param file: 上传文件
        :return: 验证结果
        """
        # 文件名检查
        if not file.filename:
            return {"error": "文件名不能为空"}

        # 检查文件类型
        file_ext = FileService.get_file_extension(file.filename)
        if file_ext not in settings.ALLOWED_FILE_TYPES:
            return {
                "error": f"不支持的文件类型: {file_ext} 仅支持 {', '.join(settings.ALLOWED_FILE_TYPES)}"
            }

        # 文件大小检查
        if file.size and file.size > settings.MAX_FILE_SIZE:
            return {"error": f"文件大小超过限制 {settings.MAX_FILE_SIZE} 字节"}

        return {"success": True}

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        获取文件扩展名
        :param filename: 文件名
        :return: 文件扩展名
        """
        return Path(filename).suffix.lower()

    @staticmethod
    async def upload_single_file(file: UploadFile) -> Dict:
        """
        上传单个文件 - 支持大文件
        :param file: 上传文件
        :return: 文件信息
        """
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        temp_path = settings.TEMP_DIR / f"{unique_filename}.tmp"
        final_path = settings.UPLOAD_DIR / unique_filename

        temp_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"[compress] 开始上传文件: {file.filename}")

        # 分块读取和写入文件
        md5_hash = hashlib.md5()
        total_size = 0

        try:
            async with aiofiles.open(temp_path, 'wb') as out_file:
                while True:
                    chunk = await file.read(settings.CHUNK_SIZE)
                    if not chunk:
                        break

                    total_size += len(chunk)

                    # 实时检查文件大小
                    if total_size > settings.MAX_FILE_SIZE:
                        raise HTTPException(
                            400,
                            f"文件 {file.filename} 大小超过限制 {settings.MAX_FILE_SIZE / (1024 * 1024):.2f} MB"
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
                "size": total_size,
                "md5": md5_hash.hexdigest(),
                "content_type": file.content_type,
                "uploaded_at": datetime.now().isoformat()
            }

        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise e

    @staticmethod
    async def cleanup_uploaded_files(uploaded_files: List[Dict]):
        """
        清理已上传的文件
        :param uploaded_files: 文件列表
        :return: 清理结果
        """
        for file_info in uploaded_files:
            try:
                file_path = Path(file_info.get("file_path", ""))
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.error(f"清理文件失败: {str(e)}")

    @staticmethod
    async def get_uploaded_files_list() -> List[Dict]:
        """
        获取已上传的文件列表
        :return: 文件列表
        """
        files = []
        if settings.UPLOAD_DIR.exists():
            for file_path in settings.UPLOAD_DIR.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
        return files
