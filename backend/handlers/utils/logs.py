import sys
import logging
import platform
from loguru import logger

# Windows系统启用ANSI支持
if platform.system() == "Windows":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取对应的 Loguru level 名称
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找原始调用栈帧，跳过 logging 内部帧
        frame = sys._getframe(6)
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging(
        level=logging.INFO, log_file="logs/app.log", rotation="500 MB"
):
    # 移除默认的 logging handler
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # 设置 loguru 的格式
    _format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.remove()  # 删除默认的日志输出

    logger.add(
        sys.stderr,
        level=level,
        format=_format
    )

    # 输出到文件
    logger.add(
        log_file,
        rotation=rotation,
        level=level,
        format=_format
    )

    # 设置 root logger 的 level
    logging.root.setLevel(level)

    return logger
