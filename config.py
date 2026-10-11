"""应用配置项。

所有可调参数集中在这里，避免散落在业务代码中。
可用环境变量覆盖常用项，便于部署到不同环境。
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def _env_flag(name: str, default: bool) -> bool:
    """读取形如 ``1/true/yes/on`` 的布尔环境变量。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# 单次请求允许的最大上传体积（MB），由 Flask 在请求体解析阶段拦截。
MAX_CONTENT_LENGTH_MB = int(os.environ.get("APP_MAX_UPLOAD_MB", "20"))

# 允许上传的图片扩展名。
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

# 生成前端预览图时的最长边（像素）；比对始终基于原图，预览仅用于界面展示。
PREVIEW_MAX_SIDE = 960

# 前端默认选中的算法 key。
DEFAULT_ALGORITHM = "histogram"

# 监听地址与端口，可用环境变量覆盖。
HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "5000"))

# 调试模式默认开启方便本地开发；生产部署时设置 APP_DEBUG=0 关闭。
DEBUG = _env_flag("APP_DEBUG", True)
USE_RELOADER = _env_flag("APP_RELOADER", DEBUG)
