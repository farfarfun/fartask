"""fartask 测试套件。

覆盖：
- 顶层包 / 子模块的 import
- 核心公开类/函数的基础调用
- TaskManager 的 CRUD 流程（真实 sqlite，隔离在 tmp_path）
- submit_task() 的 SLURM/C++ 两条真实成功路径（真实执行 g++/subprocess，
  不 mock 掉核心行为），以及"两种任务文件都不存在"的边界情况
"""

import importlib
import os
import sys

import pytest


def _reload_isolated(*mod_names):
    """清掉缓存的模块，确保下次 import 会用当前 cwd 重新初始化数据库连接。"""
    for name in mod_names:
        sys.modules.pop(name, None)


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


def test_task_model_import_has_no_side_effect(tmp_path, monkeypatch):
    """import fartask.models.task_model 不应在当前工作目录创建任何文件。"""
    monkeypatch.chdir(tmp_path)
    _reload_isolated("fartask.models.task_model")

    importlib.import_module("fartask.models.task_model")

    assert list(tmp_path.iterdir()) == []


def test_task_manager_crud_isolated(tmp_path, monkeypatch):
    """TaskManager 的基本 CRUD 流程冒烟测试（隔离在临时目录的真实 sqlite）。"""
    monkeypatch.chdir(tmp_path)
    _reload_isolated("fartask.task.manager", "fartask.models.task_model")

    manager_mod = importlib.import_module("fartask.task.manager")

    manager = manager_mod.TaskManager()
    try:
        assert (tmp_path / "tasks.db").exists()

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


def test_submit_task_slurm_path(tmp_path, monkeypatch):
    """submit_task() 的 SLURM 成功路径：检测到 config.slurm 后创建任务记录并提交。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.slurm").write_text("#!/bin/bash\necho hi\n")

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    task_dir = submit_mod.submit_task()

    assert task_dir == os.path.join(str(tmp_path), "workbench", os.path.basename(task_dir))
    assert os.path.isdir(task_dir)

    manager = submit_mod.TaskManager()
    try:
        tasks = manager.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_type == "slurm"
        assert tasks[0].status == "running"
    finally:
        manager.session.close()


def test_submit_task_cpp_path(tmp_path, monkeypatch):
    """submit_task() 的 C++ 成功路径：无 config.slurm 但有 main.cpp 时真实编译并执行。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.cpp").write_text(
        '#include <cstdio>\nint main() { printf("ok\\n"); return 0; }\n'
    )

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    task_dir = submit_mod.submit_task()

    assert os.path.exists(os.path.join(task_dir, "task.app"))

    manager = submit_mod.TaskManager()
    try:
        tasks = manager.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_type == "cpp"
        assert tasks[0].status == "completed"
    finally:
        manager.session.close()


def test_submit_task_no_recognized_file(tmp_path, monkeypatch):
    """既没有 config.slurm 也没有 main.cpp 时：创建任务目录，但不产生任务记录。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    task_dir = submit_mod.submit_task()

    assert os.path.isdir(task_dir)
    manager = submit_mod.TaskManager()
    try:
        assert manager.get_all_tasks() == []
    finally:
        manager.session.close()


def test_web_app_importable(tmp_path, monkeypatch):
    """fartask.web.app 是 __main__ 入口引用的公开子模块，应能正常 import。"""
    monkeypatch.chdir(tmp_path)
    _reload_isolated(
        "fartask.web.app",
        "fartask.task.submit",
        "fartask.task.manager",
        "fartask.models.task_model",
    )

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
