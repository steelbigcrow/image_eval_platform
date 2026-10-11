"""感知哈希相似度算法（占位实现）。

思路：把图片缩成 8x8 灰度图，与自身均值比较得到 64 位指纹，
再用汉明距离衡量差异。对缩放、轻微亮度变化、压缩噪声有一定鲁棒性，
是常见的粗粒度去重/查重方案。
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from comparators.base import BaseComparator, ComparisonResult
from comparators.registry import register

HASH_SIDE = 8


def _average_hash(image: Image.Image) -> np.ndarray:
    """生成 64 位布尔指纹。"""
    gray = image.convert("L").resize((HASH_SIDE, HASH_SIDE), Image.LANCZOS)
    pixels = np.asarray(gray, dtype=np.float64)
    return (pixels > pixels.mean()).ravel()


@register
class AverageHashComparator(BaseComparator):
    key = "ahash"
    label = "感知哈希 aHash（占位）"
    description = "64 位平均哈希 + 汉明距离，抗轻微缩放与亮度变化，粒度较粗。"

    def compare(self, source: Image.Image, target: Image.Image) -> ComparisonResult:
        source_bits = _average_hash(source)
        target_bits = _average_hash(target)

        hamming = int(np.count_nonzero(source_bits != target_bits))
        total = int(source_bits.size)
        score = (1 - hamming / total) * 100

        return ComparisonResult.from_score(
            score,
            metrics={
                "hamming_distance": hamming,
                "hash_bits": total,
                "similarity": round(score / 100, 6),
                "hash_side": HASH_SIDE,
            },
            message=f"汉明距离 {hamming}/{total}，0 表示指纹完全一致。",
        )
