"""图片上传处理：校验、解码、预览生成。

比对始终基于解码后的原图，预览图只是为了在页面上快速展示而生成的缩略版本。
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

import config


class InvalidImageError(ValueError):
    """上传内容不是合法图片，或扩展名不被允许。"""


@dataclass
class LoadedImage:
    """解码后的图片及其元信息。"""

    image: Image.Image
    filename: str
    width: int
    height: int
    mode: str
    preview_data_url: str

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "width": self.width,
            "height": self.height,
            "mode": self.mode,
            "preview": self.preview_data_url,
        }


def _validate_extension(filename: str) -> None:
    if "." not in filename:
        raise InvalidImageError(f"文件名缺少扩展名: {filename}")
    suffix = f".{filename.rsplit('.', 1)[-1].lower()}"
    if suffix not in config.ALLOWED_EXTENSIONS:
        allowed = "、".join(sorted(config.ALLOWED_EXTENSIONS))
        raise InvalidImageError(f"不支持的文件类型 {suffix}，仅支持: {allowed}")


def _to_preview_data_url(image: Image.Image) -> str:
    """生成用于前端展示的 base64 缩略图。"""
    preview = image.copy()
    preview.thumbnail((config.PREVIEW_MAX_SIDE, config.PREVIEW_MAX_SIDE), Image.LANCZOS)
    buffer = io.BytesIO()
    preview.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def load_image(stream: BinaryIO, filename: str) -> LoadedImage:
    """校验并解码一张上传的图片。

    Args:
        stream: 上传文件流。
        filename: 客户端提供的文件名，用于扩展名校验。

    Raises:
        InvalidImageError: 扩展名不支持或文件无法解析为图片。
    """

    _validate_extension(filename)
    try:
        raw = stream.read()
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError(f"无法解析图片内容: {filename}") from exc

    # 修正手机照片的 EXIF 方向，并统一成 RGB，便于后续算法处理。
    image = ImageOps.exif_transpose(image)
    had_alpha = image.mode in ("RGBA", "LA", "P")
    if had_alpha:
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    return LoadedImage(
        image=image,
        filename=filename,
        width=image.width,
        height=image.height,
        mode=image.mode,
        preview_data_url=_to_preview_data_url(image),
    )
