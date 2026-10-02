"""fartask：SLURM 集群任务与本地 C++ 任务的提交、追踪与 NiceGUI 网页看板。

公开入口在首次访问时才真正导入（`import fartask` 本身不初始化日志或数据库）：

- `submit_task`：提交当前目录下的任务（`config.slurm` 或 `main.cpp`）
- `TaskSubmissionError`：当前目录没有可提交的任务文件
- `TaskCommandError`：提交 / 编译 / 执行命令以非零状态退出
- `TaskManager`：任务记录的增删改查
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .task.manager import TaskManager as TaskManager
    from .task.submit import TaskCommandError as TaskCommandError
    from .task.submit import TaskSubmissionError as TaskSubmissionError
    from .task.submit import submit_task as submit_task

__all__ = ["TaskCommandError", "TaskManager", "TaskSubmissionError", "submit_task"]

_LAZY_EXPORTS = {
    "TaskCommandError": "fartask.task.submit",
    "TaskManager": "fartask.task.manager",
    "TaskSubmissionError": "fartask.task.submit",
    "submit_task": "fartask.task.submit",
}


def __getattr__(name: str) -> Any:
    """惰性解析公开入口，避免 `import fartask` 产生日志 / 数据库副作用。

    Args:
        name: 要访问的属性名。

    Returns:
        对应的公开类或函数。

    Raises:
        AttributeError: 名称不属于本包的公开入口。
    """
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module_name), name)


def __dir__() -> list[str]:
    """让 `dir(fartask)` 列出惰性导出的公开入口。"""
    return sorted(__all__)
