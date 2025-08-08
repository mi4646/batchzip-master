from typing import List, Optional, Union

import uuid
import shutil
import zipfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ZipService:
    """
    ZIP文件处理服务类
    """

    @staticmethod
    async def extract_zip(
            zip_path: Union[str, Path], extract_to: Union[str, Path], password: Optional[str] = None
    ) -> List[str]:
        """
        解压ZIP文件到指定目录

        :param zip_path: ZIP文件路径
        :param extract_to: 解压目录
        :param password: 解压密码（可选）
        :return: 解压的文件列表
        """
        try:
            # 确保解压目录存在
            Path(extract_to).mkdir(parents=True, exist_ok=True)

            extracted_files = []

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 如果有密码，设置密码
                if password:
                    zip_ref.setpassword(password.encode('utf-8'))

                # 解压所有文件
                for member in zip_ref.namelist():
                    # 安全检查：防止路径遍历攻击
                    member_path = Path(member)
                    if member_path.is_absolute() or ".." in str(member_path):
                        logger.warning(f"跳过不安全的文件路径: {member}")
                        continue

                    zip_ref.extract(member, extract_to)
                    extracted_files.append(str(Path(extract_to) / member))
                    logger.info(f"解压文件: {member}")

            logger.info(f"ZIP文件解压完成，共解压 {len(extracted_files)} 个文件")
            return extracted_files

        except zipfile.BadZipFile:
            raise Exception("无效的ZIP文件")
        except RuntimeError as e:
            if "Bad password" in str(e):
                raise Exception("解压密码错误")
            else:
                raise Exception(f"解压失败: {str(e)}")
        except Exception as e:
            raise Exception(f"解压过程中发生错误: {str(e)}")

    @staticmethod
    async def create_zip_from_directory(
            source_dir: Union[str, Path],
            output_path: Union[str, Path],
            password: Optional[str] = None,
            compression_level: int = 6
    ) -> str:
        """
        从目录创建ZIP文件

        :param source_dir: 源目录路径
        :param output_path: 输出ZIP文件路径
        :param password: 压缩密码（可选）
        :param compression_level: 压缩级别 (0-9)
        :return: 输出ZIP文件路径
        """
        try:
            source_path = Path(source_dir)
            if not source_path.exists():
                raise Exception(f"源目录不存在: {source_dir}")

            # 创建ZIP文件
            with zipfile.ZipFile(
                    output_path,
                    'w',
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=compression_level
            ) as zip_ref:

                # 如果设置了密码，添加密码保护
                if password:
                    zip_ref.setpassword(password.encode('utf-8'))

                # 遍历目录中的所有文件
                for file_path in source_path.rglob('*'):
                    if file_path.is_file():
                        # 计算相对路径
                        relative_path = file_path.relative_to(source_path)
                        zip_ref.write(file_path, relative_path)
                        logger.debug(f"添加文件到ZIP: {relative_path}")

            logger.info(f"ZIP文件创建完成: {output_path}")
            return output_path

        except Exception as e:
            raise Exception(f"创建ZIP文件失败: {str(e)}")

    @staticmethod
    async def rezip_file(
            zip_path: Union[str, Path],
            output_path: Union[str, Path],
            extract_password: Optional[str] = None,
            compress_password: Optional[str] = None,
            compression_level: int = 6
    ) -> str:
        """
        重新压缩ZIP文件（解压后重新压缩，支持密码转换）

        :param zip_path: 原始ZIP文件路径
        :param output_path: 输出ZIP文件路径
        :param extract_password: 解压密码（可选）
        :param compress_password: 压缩密码（可选）
        :param compression_level: 压缩级别 (0-9)
        :return: 重新压缩后的ZIP文件路径
        """

        # 创建临时解压目录
        temp_extract_dir = Path("temp") / f"extract_{uuid.uuid4().hex}"

        try:
            # 解压原始ZIP文件
            logger.debug(f"开始解压文件: {zip_path}")
            extracted_files = await ZipService.extract_zip(
                zip_path,
                str(temp_extract_dir),
                extract_password
            )

            if not extracted_files:
                raise Exception("解压后没有找到任何文件")

            # 重新压缩
            logger.info(f"开始重新压缩到: {output_path}")
            result_path = await ZipService.create_zip_from_directory(
                str(temp_extract_dir),
                output_path,
                compress_password,
                compression_level
            )

            return result_path

        finally:
            # 清理临时目录
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
                logger.info(f"清理临时目录: {temp_extract_dir}")

    @staticmethod
    async def get_zip_info(zip_path: Union[str, Path], password: Optional[str] = None) -> dict:
        """
        获取ZIP文件信息
        :param zip_path: ZIP文件路径
        :param password: 解压密码（可选）
        :return: ZIP文件信息
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                if password:
                    zip_ref.setpassword(password.encode('utf-8'))

                file_list = []
                total_size = 0

                for info in zip_ref.infolist():
                    file_info = {
                        "filename": info.filename,
                        "file_size": info.file_size,
                        "compress_size": info.compress_size,
                        "compress_type": info.compress_type,
                        "date_time": f"{info.date_time[0]}-{info.date_time[1]:02d}-{info.date_time[2]:02d} "
                                     f"{info.date_time[3]:02d}:{info.date_time[4]:02d}:{info.date_time[5]:02d}"
                    }
                    file_list.append(file_info)
                    total_size += info.file_size

                return {
                    "file_count": len(file_list),
                    "total_size": total_size,
                    "files": file_list
                }

        except Exception as e:
            raise Exception(f"获取ZIP文件信息失败: {str(e)}")
