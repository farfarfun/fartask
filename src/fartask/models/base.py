"""任务基类占位实现（当前尚未接入具体任务执行逻辑）。"""

from typing import Any


class Task:
    """任务基类：当前是空壳实现，接受任意参数，`run` 不做任何事。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def run(self, *args: Any, **kwargs: Any) -> None:
        """执行任务（当前是空壳实现，不做任何事）。"""
