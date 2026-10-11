"""比对算法的抽象定义。

新增算法只需要继承 :class:`BaseComparator` 并实现 :meth:`BaseComparator.compare`，
再用 ``@register`` 装饰器注册即可，前端下拉框会自动出现新算法，
后端接口与前端页面都不需要改动。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

from PIL import Image


@dataclass
class ComparisonResult:
    """一次比对的统一结果。

    Attributes:
        score: 归一化到 0~100 的相似度分数，越大越相似。
        metrics: 算法自报的中间指标，直接透传给前端展示。
        message: 可选的补充说明。
    """

    score: float
    metrics: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    @classmethod
    def from_score(
        cls,
        score: float,
        metrics: dict[str, Any] | None = None,
        message: str = "",
    ) -> ComparisonResult:
        """构造结果并把分数裁剪到合法区间。"""
        return cls(
            score=min(100.0, max(0.0, float(score))),
            metrics=metrics or {},
            message=message,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseComparator(ABC):
    """所有比对算法的基类。"""

    #: 算法唯一标识，用于接口参数与前端展示。
    key: str = "base"
    #: 界面上展示的名称。
    label: str = "Base"
    #: 界面上展示的一句话说明。
    description: str = ""

    @abstractmethod
    def compare(self, source: Image.Image, target: Image.Image) -> ComparisonResult:
        """比对原图与目标图。

        Args:
            source: 原图，已转换为 RGB 模式。
            target: 目标图，已转换为 RGB 模式。

        Returns:
            统一的比对结果对象。
        """
        raise NotImplementedError
