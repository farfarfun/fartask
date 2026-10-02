# Changelog

## 1.0.8

### 新增

- 顶层包 `fartask` 惰性导出真实公开入口：`submit_task` / `TaskSubmissionError` / `TaskCommandError` / `TaskManager`（惰性导入，`import fartask` 不再初始化日志或数据库）。
- `fartask.models` 导出 `TaskModel` / `get_engine` / `get_session_factory` / `session`。
- 新增 `TaskCommandError`：外部命令非零退出或执行失败时抛出，带退出码与合并输出。
- 补充测试：顶层惰性导出与 import 无副作用、默认命令执行器的输出捕获 / 含空格参数 / 非零退出码抛错、真实编译失败落到 `failed` 状态。

### 修复

- `python -m fartask` 此前根本起不来：NiceGUI 的自动重载不支持 `python -m <package>`，startup 阶段直接抛 `RuntimeError` 退出，README 的看板示例与 `scripts/setup.sh` 的 `run`/`start` 全是死路。`ui.run` 改为 `reload=False, show=False`（服务进程不需要自动重载与打开浏览器），并补端到端测试：真实起进程并断言 `/` 返回 200。
- Shell 命令执行改用组织包 `funshell`（SPEC §2），不再直接使用裸 `subprocess`；用 `shlex.join` 转义参数并由 shell 回传退出码，保留参数不被二次解析、`cwd`、输出捕获与失败抛错语义。
- `scripts/setup.sh` 不再只靠 `kill -0` 判断服务身份：`start`/`stop`/`status` 先用 `.run/fartask-<env>.cmd` 的命令行指纹核对 `/proc/<pid>/cmdline`（无 `/proc` 时回退 `ps`），PID 被复用时按陈旧 PID 处理且不发送终止信号。
- README 安装方式与当前发布状态一致：`fartask` 尚未发布到 PyPI，改为源码安装，并说明 `prod` 需要从包索引安装的正式包、当前应使用 `dev`。

### 变更

- 移除空壳公开类 `fartask.Task`（`fartask.models.base`）：它接受任意参数且 `run()` 不做任何事，不作为公开 API 保留。
- `main()` / `TaskManager.__init__` 补齐中文 docstring，说明参数、返回值与副作用。

### 废弃

（无）

## 1.0.7

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
