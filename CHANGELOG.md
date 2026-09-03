# Changelog

## Unreleased

### 新增

- 新增 `scripts/setup.sh`，统一 `run`/`start`/`stop`/`restart`/`status` 生命周期管理（NiceGUI 网页看板），`prod` 模式拒绝从源码目录启动。
- `pyproject.toml` 补充 `license = "MIT"` 声明。
- README 补充组织介绍区块与 MIT 协议说明，以及 `scripts/setup.sh` 用法。

### 修复

- `fartask.models.task_model` 不再在模块 import 时创建数据库引擎/建表（`create_engine("sqlite:///tasks.db", echo=True)`），改为惰性初始化，避免任意 import 都在当前工作目录写 `tasks.db` 并输出 SQL 诊断日志。
- `fartask.task.submit.submit_task` 中 `os.path.join(HOME, "/workbench", ts)` 因第二个参数以 `/` 开头，实际结果恒为 `/workbench/<ts>` 而非 `$HOME/workbench/<ts>`；改为 `"workbench"`，行为符合预期。
- 依赖统一维护在 `pyproject.toml`，删除与之不同步、且缺版本下限的 `requirements.txt`；新增 `uv.lock`。

### 变更

- 公开类/函数补充类型标注（`list[...]`/`... | None`）与中文 docstring。
- 补充 `tests/`：`submit_task` 的 SLURM/C++ 成功路径改为在隔离临时目录下真实执行，不再整体 mock 掉核心行为。

### 废弃

（无）

## 1.0.6

### 新增

- 初始版本：SLURM/C++ 任务提交与追踪，NiceGUI 网页看板。

### 修复

（无）

### 变更

（无）

### 废弃

（无）
