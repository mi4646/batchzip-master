import sys
import logging
import platform
from loguru import logger
from typing import Final, Literal

# 定义日志级别，用于类型提示
LogLevel = Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]

# --- Windows ANSI支持 ---
if platform.system() == "Windows":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception as e:
        logger.warning(f"无法启用Windows ANSI支持: {e}")


# --- 拦截标准logging模块的处理器 ---
class InterceptHandler(logging.Handler):
    """
    一个日志处理器，用于拦截Python标准logging的记录，并将其发送到Loguru。
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage()
        )


# --- 日志配置主函数 ---
def setup_logging(
        level: LogLevel = "INFO",
        log_file: str = "logs/app.log",
        rotation: str = "500 MB"
) -> None:
    """
    设置全局日志系统，并自定义INFO日志级别颜色。
    """
    # 自定义INFO级别颜色为浅蓝色
    # logger.level("INFO", color="<light-green>")

    # 定义通用的日志格式
    log_format: Final[str] = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # 移除所有默认处理器
    logger.remove()

    # 添加控制台处理器（sys.stderr），支持颜色输出
    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        colorize=True
    )

    # 添加文件处理器，保持纯文本
    logger.add(
        log_file,
        rotation=rotation,
        level=level,
        format=log_format,
        colorize=False,
        compression="zip",
        encoding="utf-8"
    )

    # 整合标准logging
    logging.basicConfig(handlers=[InterceptHandler()], level=level)


if __name__ == "__main__":
    setup_logging(level="INFO")
    logger.info("这是一条自定义的INFO日志。它现在应该是蓝色的。")
    logger.warning("这条警告日志应该保持默认的黄色。")

    std_logger = logging.getLogger("my_module")
    std_logger.info("这条来自标准logging的INFO日志也应该是蓝色的！")
