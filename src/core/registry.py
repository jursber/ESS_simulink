"""调度算法注册表 — 支持插拔式算法切换。"""
from __future__ import annotations

from typing import Callable, Any

# 算法注册表：name -> {fn, desc, params_schema}
ALGORITHM_REGISTRY: dict[str, dict[str, Any]] = {}


def register_algorithm(name: str, description: str):
    """装饰器，注册一个调度算法。"""
    def decorator(fn: Callable):
        ALGORITHM_REGISTRY[name] = {
            "fn": fn,
            "desc": description,
        }
        return fn
    return decorator


def get_algorithm(name: str) -> Callable:
    """获取已注册的算法函数。"""
    if name not in ALGORITHM_REGISTRY:
        raise ValueError(f"未知算法: {name}，可用: {list(ALGORITHM_REGISTRY.keys())}")
    return ALGORITHM_REGISTRY[name]["fn"]


def list_algorithms() -> list[dict[str, str]]:
    """返回所有已注册算法的列表。"""
    return [
        {"id": k, "desc": v["desc"]}
        for k, v in ALGORITHM_REGISTRY.items()
    ]
