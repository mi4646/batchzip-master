import os
from typing import Dict, List, Union
from pydantic_settings import BaseSettings


def env(key, type_, default=None):
    """
    根据环境变量键获取其值，并转换为指定类型。
    :param key:
    :param type_:
    :param default:
    :return:
    """
    from os import environ

    if key not in environ:
        return default

    val = environ[key]

    if type_ is str:
        # 移除两端的引号（单引号、双引号）
        return val.strip('"').strip("'")
    if type_ is bool:
        if val.lower() in ["1", "True", "true", "yes", "y", "ok", "on"]:
            return True
        if val.lower() in ["0", "False", "false", "no", "n", "nok", "off"]:
            return False
        raise ValueError(
            "Invalid environment variable '%s' (expected a boolean): '%s'" % (key, val)
        )
    if type_ is int:
        try:
            return int(val)
        except ValueError:
            raise ValueError(
                "Invalid environment variable '%s' (expected an integer): '%s'" % (key, val)
            ) from None
    raise ValueError("The requested type '%s' is not supported" % type_.__name__)


class Settings(BaseSettings):
    ENV: str = "base"

    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 项目名称
    PROJECT_NAME: str = env('PROJECT_NAME', str, 'fastapi-test')
    HOST: str = env('HOST', str, '0.0.0.0')
    PORT: int = env('PORT', int, 8000)
    # 是否开启debug模式
    DEBUG: bool = env('DEBUG', bool, True)
    # 项目版本
    VERSION: str = env('VERSION', str, '0.0.1')
    # 是否启用热重载
    RELOAD: bool = env('RELOAD', bool, True)
    # 工作进程数
    WORKERS: int = env('WORKERS', int, 1)

    # CORS 配置
    ALLOWED_HOSTS: List[str] = ['*']
    ALLOWED_METHODS: List[str] = ['*']
    ALLOWED_HEADERS: List[str] = ['*']



    # REDIS_URI 配置
    REDIS_CONFIG: Dict[str, Union[str, int, bool]] = {
        'host': env('REDIS_HOST', str, 'localhost'),
        'password': env('REDIS_PASSWORD', str, ''),
        'port': env('REDIS_PORT', int, 6379),
        'db': env('REDIS_DB', int, 0),
        'decode_responses': env('REDIS_DECODE_RESPONSES', bool, True),
    }

    # 日志配置
    LOG_LEVEL: str = "INFO"
    AUTO_DELETE_ERROR_LOGS_ENABLED: bool = True
    AUTO_DELETE_ERROR_LOGS_DAYS: int = 7
    AUTO_DELETE_REQUEST_LOGS_ENABLED: bool = False
    AUTO_DELETE_REQUEST_LOGS_DAYS: int = 30
