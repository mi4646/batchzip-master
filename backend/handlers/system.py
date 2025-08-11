from fastapi import APIRouter
import psutil
from typing import Final

router = APIRouter(tags=['system'])


@router.get(
    "/info",
    summary="获取系统CPU和内存使用情况",
    description="""
返回CPU使用率、内存使用率、总内存和已用内存，用于性能监控。

各项指标说明：
- cpu_percent: CPU使用率
- memory_percent: 内存使用率
- memory_total_gb: 总内存
- memory_used_gb: 已用内存
- memory_free_gb: 可用内存
"""
)
async def get_system_stats():
    """
    获取并返回系统的CPU和内存使用情况。

    Returns:
        SystemStats: 包含系统CPU和内存指标的对象。
    """
    # 获取CPU使用率，interval=1会等待1秒以获取更准确的数据
    cpu_percent: Final[float] = psutil.cpu_percent(interval=1)

    # 获取虚拟内存信息
    memory_info = psutil.virtual_memory()
    memory_percent: Final[float] = memory_info.percent

    # 将内存单位从字节转换为GB，并保留两位小数
    memory_total_gb: Final[float] = round(memory_info.total / (1024 ** 3), 2)
    memory_used_gb: Final[float] = round(memory_info.used / (1024 ** 3), 2)

    # 返回一个包含所有指标的字典，FastAPI会自动将其转换为SystemStats模型
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "memory_total_gb": memory_total_gb,
        "memory_used_gb": memory_used_gb,
        "memory_free_gb": round(memory_info.free / (1024 ** 3), 2),
    }
