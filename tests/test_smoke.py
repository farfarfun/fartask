"""轻量级冒烟测试套件（smoke tests）。

该仓库（farfarfun/fartask）此前没有任何 tests/ 目录。

这些测试只做最基础的“能不能跑起来”的验证：
- 顶层包 / 子模块能否正常 import
- 核心公开类/函数用简单参数调用是否报错
- 任何会连接真实数据库/发起真实 shell 调用的地方都用 mock 隔离

已知问题（发现但按要求不在本测试任务中修复，见注释 / 最终汇报）：
1. `fartask.models.task_model` 在模块导入时就会以相对路径 "sqlite:///tasks.db"
   创建引擎并执行 `Base.metadata.create_all(engine)`，即无论谁在什么目录下
   import 这个模块，都会在当前工作目录下产生一个真实的 tasks.db 文件（以及
   farlog 附带产生的 logs/ 目录）。测试中我们用 tmp_path + chdir 隔离，避免
   污染仓库目录。
2. `fartask.task.submit.submit_task()` 中
   `os.path.join(os.environ["HOME"], "/workbench", timestamp)` 的第二个参数
   以 "/" 开头，会被 os.path.join 丢弃前面的部分，实际结果恒为
   "/workbench/<timestamp>"，而不是用户预期的 "$HOME/workbench/<timestamp>"。
   这会导致 os.makedirs 尝试在系统根目录下建目录（非 root 用户会因权限不足而
   失败）。这是一个业务逻辑 bug，测试中通过 mock os.makedirs / run_shell /
   TaskManager 绕开，不在本任务范围内修复。
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


def test_import_top_level_package():
    """顶层包 `fartask` 应该可以被正常导入（不触发任何真实 IO）。"""
    import fartask

    assert hasattr(fartask, "Task")


def test_task_class_basic_usage():
    """核心公开类 Task 用简单参数构造和调用应不报错。"""
    from fartask import Task

    task = Task()
    assert task.run() is None
    # 任意参数也应该被静默接受（当前实现是空壳）
    task2 = Task(1, 2, foo="bar")
    assert task2.run(a=1, b=2) is None


def test_models_package_importable():
    """fartask.models 子包能正常导入并暴露 Task。"""
    from fartask.models import Task
    from fartask.models.base import Task as BaseTask

    assert Task is BaseTask


def test_task_manager_crud_isolated(tmp_path, monkeypatch):
    """TaskManager 的基本 CRUD 流程冒烟测试。

    fartask.models.task_model 在 import 时会用相对路径创建 sqlite 文件，
    因此这里先 chdir 到隔离的临时目录，并清掉可能已缓存的模块，确保
    sqlite 文件落在 tmp_path 而不是污染仓库目录或复用其它测试遗留的状态。
    """
    monkeypatch.chdir(tmp_path)

    for mod_name in (
        "fartask.task.manager",
        "fartask.models.task_model",
    ):
        sys.modules.pop(mod_name, None)

    task_model_mod = importlib.import_module("fartask.models.task_model")
    manager_mod = importlib.import_module("fartask.task.manager")

    assert (tmp_path / "tasks.db").exists()

    manager = manager_mod.TaskManager()
    try:
        created = manager.create_task(
            task_dir=str(tmp_path / "task_1"),
            task_type="cpp",
            description="smoke test task",
        )
        assert created.id is not None
        assert created.status == "pending"

        fetched = manager.get_task(created.id)
        assert fetched is not None
        assert fetched.task_dir == str(tmp_path / "task_1")

        all_tasks = manager.get_all_tasks()
        assert len(all_tasks) == 1

        updated = manager.update_task_status(created.id, "completed", output="ok")
        assert updated.status == "completed"
        assert updated.output == "ok"

        assert manager.delete_task(created.id) is True
        assert manager.get_task(created.id) is None
        assert manager.delete_task(999999) is False
    finally:
        manager.session.close()

    del task_model_mod  # 仅用于避免 lint 误报未使用


def test_submit_task_smoke(tmp_path, monkeypatch):
    """submit_task() 冒烟测试：mock 掉所有真实 shell / 文件系统 / DB 交互。

    注意：submit_task 内部存在 os.path.join(home, "/workbench", ts) 的 bug
    （见文件头注释），会导致 task_dir 恒为 "/workbench/<ts>"。为了不真的在
    根目录下建目录，这里把 os.makedirs 也 mock 掉。
    """
    from fartask.task import submit as submit_mod

    monkeypatch.setenv("HOME", str(tmp_path))

    fake_manager = MagicMock()
    with patch.object(submit_mod, "TaskManager", return_value=fake_manager), patch.object(
        submit_mod, "run_shell"
    ) as mock_run_shell, patch.object(submit_mod.os, "makedirs") as mock_makedirs, patch.object(
        submit_mod.os.path, "exists", return_value=False
    ):
        result = submit_mod.submit_task()

    assert result is not None
    mock_makedirs.assert_called_once()
    mock_run_shell.assert_called_once()
    # 没有检测到 config.slurm / main.cpp，因此不应该真正创建任务记录
    fake_manager.create_task.assert_not_called()


def test_web_app_importable(tmp_path, monkeypatch):
    """fartask.web.app 是 __main__ 入口引用的公开子模块，应能正常 import。

    该模块 import 时会在模块级别构造一个真实的 TaskManager()（连接 sqlite），
    因此同样通过 chdir 到隔离目录来避免污染仓库工作目录。不调用
    start_web_server()，因为那会真的启动一个 web 服务进程。
    """
    monkeypatch.chdir(tmp_path)

    for mod_name in (
        "fartask.web.app",
        "fartask.task.submit",
        "fartask.task.manager",
        "fartask.models.task_model",
    ):
        sys.modules.pop(mod_name, None)

    app_mod = importlib.import_module("fartask.web.app")

    assert callable(app_mod.start_web_server)
    assert callable(app_mod.create_task_list)
    assert callable(app_mod.main_page)


def test_cli_entry_point_absent():
    """确认本仓库当前未声明 [project.scripts] CLI 入口。

    若未来添加了 CLI 入口，应在此补充对应的 --help 冒烟测试
    （click.testing.CliRunner 或 subprocess + --help）。此处用
    pytest.skip 明确标注原因，而不是静默省略。
    """
    pytest.skip("当前 pyproject.toml 未声明 [project.scripts]，无 CLI 入口可测试")
