"""fartask 测试套件。

覆盖：
- 顶层包 / 子模块的 import 与惰性公开入口
- TaskManager 的 CRUD 流程（真实 sqlite，隔离在 tmp_path）
- submit_task() 的 SLURM/C++ 两条真实成功路径（真实执行 g++，不 mock 掉核心行为），
  以及"两种任务文件都不存在"、命令失败、路径含空格等边界情况
- 默认命令执行器（funshell）的输出捕获与非零退出码抛错行为
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _reload_isolated(*mod_names):
    """清掉缓存的模块，确保下次 import 会用当前 cwd 重新初始化数据库连接。"""
    for name in mod_names:
        sys.modules.pop(name, None)


def test_import_top_level_package():
    """顶层包 `fartask` 应该可以被正常导入（不触发任何真实 IO）。"""
    import fartask

    assert set(fartask.__all__) == {
        "Task",
        "TaskCommandError",
        "TaskManager",
        "TaskSubmissionError",
        "submit_task",
    }


def test_top_level_lazy_exports():
    """顶层惰性导出应解析到真实实现，未知属性要抛 AttributeError。"""
    import fartask
    from fartask.task.manager import TaskManager
    from fartask.task.submit import (
        TaskCommandError,
        TaskSubmissionError,
        submit_task,
    )

    assert fartask.TaskManager is TaskManager
    assert fartask.submit_task is submit_task
    assert fartask.TaskSubmissionError is TaskSubmissionError
    assert fartask.TaskCommandError is TaskCommandError
    assert "submit_task" in dir(fartask)
    with pytest.raises(AttributeError):
        getattr(fartask, "not_a_public_entry")  # noqa: B009


def test_deprecated_task_compatibility_entry():
    """旧 Task 入口保留空壳行为，并在使用时提供可操作的迁移提示。"""
    import fartask

    with pytest.deprecated_call(match="submit_task"):
        task = fartask.Task("ignored", named="ignored")

    assert task.run() is None


def test_top_level_import_has_no_side_effect(tmp_path, monkeypatch):
    """`import fartask` 本身不应创建日志目录或数据库文件。"""
    monkeypatch.chdir(tmp_path)
    _reload_isolated("fartask")

    importlib.import_module("fartask")

    assert list(tmp_path.iterdir()) == []


def test_models_package_importable():
    """fartask.models 子包应暴露数据模型与会话入口。"""
    from fartask.models import TaskModel, get_engine, get_session_factory, session
    from fartask.models.task_model import TaskModel as DirectTaskModel

    assert TaskModel is DirectTaskModel
    assert callable(get_engine)
    assert callable(get_session_factory)
    assert callable(session)


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


def test_database_paths_are_independent(tmp_path):
    """不同数据库连接串应获得各自的引擎和会话。"""
    from fartask.models.task_model import get_engine, session

    first_url = f"sqlite:///{tmp_path / 'first.db'}"
    second_url = f"sqlite:///{tmp_path / 'second.db'}"

    assert get_engine(first_url) is not get_engine(second_url)
    first_session = session(first_url)
    second_session = session(second_url)
    try:
        assert first_session.get_bind() is get_engine(first_url)
        assert second_session.get_bind() is get_engine(second_url)
    finally:
        first_session.close()
        second_session.close()


def test_submit_task_slurm_path(tmp_path, monkeypatch):
    """submit_task() 的 SLURM 成功路径：检测到 config.slurm 后创建任务记录并提交。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.slurm").write_text("#!/bin/bash\necho hi\n")

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    calls = []

    def command_runner(command, cwd):
        calls.append((command, cwd))
        return "Submitted batch job 123"

    task_dir = submit_mod.submit_task(command_runner)

    assert task_dir == os.path.join(
        str(tmp_path), "workbench", os.path.basename(task_dir)
    )
    assert os.path.isdir(task_dir)
    assert calls == [(["sbatch", "config.slurm"], task_dir)]

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
    """既没有 config.slurm 也没有 main.cpp 时应明确拒绝提交。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    with pytest.raises(submit_mod.TaskSubmissionError, match=str(tmp_path)):
        submit_mod.submit_task()

    assert not (tmp_path / "workbench").exists()


@pytest.mark.parametrize("task_file", ["config.slurm", "main.cpp"])
def test_submit_task_command_failure_is_recorded(tmp_path, monkeypatch, task_file):
    """提交、编译或执行命令失败后，任务记录必须变为 failed。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / task_file).write_text("invalid task")

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    def failing_runner(command, cwd):
        raise subprocess.CalledProcessError(1, command, stderr="command failed")

    with pytest.raises(subprocess.CalledProcessError):
        submit_mod.submit_task(failing_runner)

    manager = submit_mod.TaskManager()
    try:
        tasks = manager.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].status == "failed"
        assert "returned non-zero exit status 1" in tasks[0].output
    finally:
        manager.session.close()


def test_submit_task_execution_failure_is_recorded(tmp_path, monkeypatch):
    """C++ 编译成功但执行失败时，任务记录必须变为 failed。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.cpp").write_text("int main() { return 0; }")

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    def command_runner(command, cwd):
        if command == ["./task.app"]:
            raise subprocess.CalledProcessError(1, command)
        return "compiled"

    with pytest.raises(subprocess.CalledProcessError):
        submit_mod.submit_task(command_runner)

    manager = submit_mod.TaskManager()
    try:
        tasks = manager.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].status == "failed"
    finally:
        manager.session.close()


def test_submit_task_supports_home_path_with_spaces(tmp_path, monkeypatch):
    """任务目录含空格时，命令参数与工作目录仍保持完整。"""
    home = tmp_path / "home with spaces"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.slurm").write_text("#!/bin/bash\n")

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")
    calls = []

    def command_runner(command, cwd):
        calls.append((command, cwd))
        return "submitted"

    task_dir = submit_mod.submit_task(command_runner)

    assert calls == [(["sbatch", "config.slurm"], task_dir)]
    assert task_dir.startswith(str(home))


def test_default_command_runner_captures_output_in_cwd(tmp_path):
    """默认命令执行器应在指定工作目录执行并返回捕获到的输出。"""
    from fartask.task.submit import _run_command

    (tmp_path / "payload.txt").write_text("hello\n")

    assert _run_command(["cat", "payload.txt"], str(tmp_path)) == "hello"


def test_default_command_runner_handles_paths_with_spaces(tmp_path):
    """参数含空格时必须整体传递，不能被 shell 拆成多个参数。"""
    from fartask.task.submit import _run_command

    work_dir = tmp_path / "dir with spaces"
    work_dir.mkdir()
    (work_dir / "file with spaces.txt").write_text("ok\n")

    assert _run_command(["cat", "file with spaces.txt"], str(work_dir)) == "ok"


def test_default_command_runner_raises_on_non_zero_exit(tmp_path):
    """命令退出码非零时必须抛错，并带上退出码与合并输出。"""
    from fartask.task.submit import TaskCommandError, _run_command

    with pytest.raises(TaskCommandError) as excinfo:
        _run_command(["sh", "-c", "echo boom >&2; exit 3"], str(tmp_path))

    assert excinfo.value.returncode == 3
    assert "boom" in excinfo.value.output


def test_submit_task_real_compile_failure_marks_failed(tmp_path, monkeypatch):
    """用默认执行器真实编译失败时，必须抛错并把任务记录标记为 failed。"""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.cpp").write_text("this is not valid c++\n")

    _reload_isolated(
        "fartask.task.submit", "fartask.task.manager", "fartask.models.task_model"
    )
    submit_mod = importlib.import_module("fartask.task.submit")

    with pytest.raises(submit_mod.TaskCommandError):
        submit_mod.submit_task()

    manager = submit_mod.TaskManager()
    try:
        tasks = manager.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].status == "failed"
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


def _free_port():
    """取一个当前空闲的本地端口。"""
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_python_m_fartask_serves_dashboard(tmp_path):
    """README 记录的 `python -m fartask` 必须真的能起服务并响应 HTTP 请求。

    NiceGUI 的自动重载不支持 `python -m <package>`，开着会在 startup 阶段抛
    RuntimeError 并退出——这条测试就是守住这个回归。
    """
    import time
    import urllib.error
    import urllib.request

    port = _free_port()
    # NiceGUI 看到继承来的 PYTEST_CURRENT_TEST 会切到它自己的 screen-test 模式，
    # 这里要测的是普通启动路径，所以去掉这个变量。
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    process = subprocess.Popen(
        [sys.executable, "-m", "fartask", "--host", "127.0.0.1", "--port", str(port)],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 90
        last_error = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(f"看板进程提前退出：\n{process.stdout.read()}")
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/", timeout=2
                ) as response:
                    assert response.status == 200
                    return
            except (urllib.error.URLError, OSError) as exc:  # 服务还没起来
                last_error = exc
                time.sleep(0.5)
        pytest.fail(f"看板在 90s 内未就绪，最后一次错误：{last_error}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=20)


def test_cli_entry_point_declared():
    """安装包必须提供与产品同名的看板启动入口。"""
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    assert 'fartask = "fartask.__main__:main"' in pyproject.read_text()
