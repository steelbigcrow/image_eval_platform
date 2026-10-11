"""算法包。

导入本包时自动完成所有内置算法的注册，新增算法文件后在这里补充一行导入即可。
"""

from comparators import ahash, histogram, pixel  # noqa: F401  (导入即注册)
from comparators.base import BaseComparator, ComparisonResult
from comparators.registry import get, keys, list_all, register

__all__ = [
    "BaseComparator",
    "ComparisonResult",
    "get",
    "keys",
    "list_all",
    "register",
]
