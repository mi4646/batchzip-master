import os
import importlib.util
from .base import Settings

_ENV_MAP = {
    "base": "config.base.Settings",
    "local": "config.local.LocalSettings",
    "test": "config.test.TestSettings",
    "prod": "config.prod.ProdSettings",
    "ci": "config.ci.CISettings",
}


def _get_settings_class():
    """
    根据环境变量获取配置类。
    :return: 配置类
    """
    env = os.getenv("ENV", "local").lower()
    if env not in _ENV_MAP:
        raise ValueError(f"Invalid environment: {env}. Available: {_ENV_MAP.keys()}")

    full_path = _ENV_MAP[env]
    module_path, class_name = full_path.rsplit(".", 1)

    # 检查模块是否存在
    spec = importlib.util.find_spec(module_path)
    if spec is None:
        raise ImportError(f"Module '{module_path}' not found. Please make sure the file exists.")

    # 导入模块
    module = importlib.import_module(module_path)

    # 检查类是否存在
    if not hasattr(module, class_name):
        raise AttributeError(f"Class '{class_name}' not found in module '{module_path}'.")

    return getattr(module, class_name)


# 获取设置类并实例化
SettingsClass = _get_settings_class()
settings = SettingsClass()

__all__ = ["settings"]
