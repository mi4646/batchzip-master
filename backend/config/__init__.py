import os
import importlib.util
from .base import Settings

_ENV_MAP = {
    "local": "config.local.LocalSettings",
    "test": "config.test.TestSettings",
    "prod": "config.prod.ProdSettings",
    "ci": "config.ci.CISettings",
    # 如果没有指定，默认使用 'base' 配置
    "base": "config.base.Settings",
}


def load_settings():
    """
    根据环境变量动态加载并返回配置类的实例。
    """
    env = os.getenv("ENV", "local").lower()

    # 获取完整的模块路径和类名
    full_path = _ENV_MAP.get(env)
    if not full_path:
        raise ValueError(f"Invalid environment: {env}. Available: {_ENV_MAP.keys()}")

    module_path, class_name = full_path.rsplit(".", 1)

    # 动态导入模块和类
    try:
        module = importlib.import_module(module_path)
        settings_class = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise RuntimeError(f"Failed to load settings for environment '{env}': {e}")

    return settings_class()


# 在模块被导入时，自动加载并实例化配置对象
settings = load_settings()

__all__ = ["settings"]
