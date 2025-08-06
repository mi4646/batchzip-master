import redis.asyncio as redis
from backend.handlers.utils.logs import logger
from backend.config import settings as config


async def init_redis_client(raise_on_failure: bool = False) -> redis.Redis:
    """
    初始化 Redis 客户端，并尝试连接。
    """
    client = redis.Redis(**config.REDIS_CONFIG)
    try:
        pong = await client.ping()
        if pong:
            logger.info("✅ 成功连接到 Redis")
            return client
        else:
            msg = "🔴 Redis 返回结果异常：PING 未收到 PONG"
            logger.error(msg)
            if raise_on_failure:
                raise ConnectionError(msg)
    except (redis.ConnectionError, redis.TimeoutError, redis.RedisError) as e:
        logger.error(f"🔴 Redis 连接失败: {e}")
        if raise_on_failure:
            raise
    return client
