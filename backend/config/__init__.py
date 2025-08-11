# backend/config/__init__.py

import os
import importlib.util
from .base import Settings

# ⚠️ 关键修改：将所有路径都改为从 'backend' 包开始的绝对路径
_ENV_MAP = {
    "local": "backend.config.local.LocalSettings",
    "test": "backend.config.test.TestSettings",
    "prod": "backend.config.prod.ProdSettings",
    "ci": "backend.config.ci.CISettings",
    "base": "backend.config.base.Settings",
}


def load_settings():
    """
    根据环境变量动态加载并返回配置类的实例。
    """
    env = os.getenv("ENV", "local").lower()

    full_path = _ENV_MAP.get(env)
    if not full_path:
        raise ValueError(f"Invalid environment: {env}. Available: {_ENV_MAP.keys()}")

    # 路径解析保持不变，因为 full_path 已经是完整的
    module_path, class_name = full_path.rsplit(".", 1)

    try:
        module = importlib.import_module(module_path)
        settings_class = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        # 错误信息会更准确，因为它现在知道要找 'backend.config.local'
        raise RuntimeError(f"Failed to load settings for environment '{env}': {e}")

    return settings_class()


settings = load_settings()

__all__ = ["settings"]
