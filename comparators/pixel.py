"""逐像素差异算法（占位实现）。

思路：把两张图统一缩放到相同尺寸后逐像素比较，用 RMSE 推导相似度。
完全不做特征提取，纯像素对齐，因此对裁剪、旋转、缩放非常敏感，
适合作为"像素级是否一致"的严格基线。
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from comparators.base import BaseComparator, ComparisonResult
from comparators.registry import register

# 统一比对时使用的画布尺寸，避免分辨率不同直接报错。
CANVAS = (256, 256)


def _to_array(image: Image.Image, size: tuple[int, int] = CANVAS) -> np.ndarray:
    resized = image.convert("RGB").resize(size, Image.LANCZOS)
    return np.asarray(resized, dtype=np.float64)


@register
class PixelComparator(BaseComparator):
    key = "pixel"
    label = "逐像素 RMSE（占位）"
    description = "统一缩放后逐像素比对，对裁剪与位移极其敏感，可作为严格基线。"

    def compare(self, source: Image.Image, target: Image.Image) -> ComparisonResult:
        source_arr = _to_array(source)
        target_arr = _to_array(target)

        diff = source_arr - target_arr
        rmse = float(np.sqrt((diff**2).mean()))
        mae = float(np.abs(diff).mean())

        # RMSE 归一化到 0~255，0 表示完全一致。
        normalized_rmse = rmse / 255.0
        score = max(0.0, (1.0 - normalized_rmse)) * 100

        # 峰值信噪比：数值越大表示噪声占比越低。
        psnr = float("inf") if rmse == 0 else float(20 * np.log10(255.0 / rmse))

        return ComparisonResult.from_score(
            score,
            metrics={
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "psnr_db": round(psnr, 2),
                "canvas": f"{CANVAS[0]}x{CANVAS[1]}",
                "source_size": f"{source.width}x{source.height}",
                "target_size": f"{target.width}x{target.height}",
                "size_matched": source.size == target.size,
            },
            message=f"已统一缩放到 {CANVAS[0]}x{CANVAS[1]} 再逐像素比较。",
        )
