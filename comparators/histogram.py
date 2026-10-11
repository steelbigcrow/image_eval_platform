"""颜色直方图相似度算法（占位实现）。

思路：把图片转成 HSV，取 H-S 联合直方图，用交集/并集（IoU）衡量分布一致性。
优点是对平移、轻微缩放不敏感；缺点是完全不关心空间结构，
两张配色相同但构图完全不同的图也会拿到高分。

该实现主要用于打通链路，后续可替换为更合适的算法。
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from comparators.base import BaseComparator, ComparisonResult
from comparators.registry import register

H_BINS = 32
S_BINS = 32


def _hsv_histogram(image: Image.Image) -> np.ndarray:
    """计算归一化的 H-S 联合直方图。"""
    hsv = np.asarray(image.convert("HSV"), dtype=np.float64)
    hue = (hsv[..., 0] / 255.0 * H_BINS).astype(np.int32) % H_BINS
    sat = (hsv[..., 1] / 255.0 * S_BINS).astype(np.int32) % S_BINS
    flat = hue * S_BINS + sat
    hist = np.bincount(flat.ravel(), minlength=H_BINS * S_BINS).astype(np.float64)
    total = hist.sum()
    return hist / total if total else hist


@register
class HistogramComparator(BaseComparator):
    key = "histogram"
    label = "颜色直方图（占位）"
    description = "比较 HSV 颜色分布，忽略构图与空间位置，用于快速初筛。"

    def compare(self, source: Image.Image, target: Image.Image) -> ComparisonResult:
        source_hist = _hsv_histogram(source)
        target_hist = _hsv_histogram(target)

        intersection = float(np.minimum(source_hist, target_hist).sum())
        union = float(np.maximum(source_hist, target_hist).sum())
        score = intersection / union * 100 if union else 0.0

        # 余弦相似度作为交叉验证，避免单一指标过于乐观。
        denominator = float(np.linalg.norm(source_hist) * np.linalg.norm(target_hist))
        cosine = float(source_hist @ target_hist / denominator) if denominator else 0.0

        return ComparisonResult.from_score(
            score,
            metrics={
                "intersection": round(intersection, 6),
                "union": round(union, 6),
                "histogram_iou": round(score / 100, 6),
                "histogram_cosine": round(cosine, 6),
                "bins": H_BINS * S_BINS,
            },
            message="颜色分布相似度，不反映空间布局，仅作占位参考。",
        )
