from .base import *


class LocalSettings(Settings):
    ENV: str = "local"

    # REDIS_URI 配置
    REDIS_PORT: int = 6379
    REDIS_HOST: str = '192.168.2.252'
    REDIS_PASSWORD: str = ''
    REDIS_DB: int = 15

    REDIS_CONFIG: Dict[str, Union[str, int, bool]] = {
        'host': env('REDIS_HOST', str, REDIS_HOST),
        'password': env('REDIS_PASSWORD', str, REDIS_PASSWORD),
        'port': env('REDIS_PORT', int, REDIS_PORT),
        'db': env('REDIS_DB', int, REDIS_DB),
        'decode_responses': env('REDIS_DECODE_RESPONSES', bool, True),
    }
