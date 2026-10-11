"""算法注册表。

提供一个极简的注册/查找机制，使算法实现与业务代码解耦。
"""

from __future__ import annotations

from comparators.base import BaseComparator

_REGISTRY: dict[str, BaseComparator] = {}


class AlgorithmNotFoundError(KeyError):
    """请求了未注册的算法时抛出。"""


def register(comparator_cls: type[BaseComparator]) -> type[BaseComparator]:
    """把算法类注册到全局表，可作为装饰器使用。"""

    key = comparator_cls.key
    if not key or key == "base":
        raise ValueError(f"算法 {comparator_cls.__name__} 必须定义唯一的 key")
    if key in _REGISTRY:
        raise ValueError(f"算法 key 重复: {key}")
    _REGISTRY[key] = comparator_cls()
    return comparator_cls


def get(key: str) -> BaseComparator:
    """按 key 获取算法实例。"""

    try:
        return _REGISTRY[key]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY)) or "(空)"
        raise AlgorithmNotFoundError(
            f"未知算法 '{key}'，当前可用: {available}"
        ) from None


def list_all() -> list[dict[str, str]]:
    """返回所有已注册算法的元信息，供前端渲染下拉框。"""

    return [
        {"key": item.key, "label": item.label, "description": item.description}
        for item in _REGISTRY.values()
    ]


def keys() -> list[str]:
    return list(_REGISTRY)
