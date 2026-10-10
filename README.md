# fartask

用于提交和追踪 SLURM 集群任务及本地 C++ 编译运行任务，并提供 NiceGUI 网页看板监控任务状态。

## 安装

```bash
pip install fartask
```

PyPI 当前发布版本为 `1.0.8`；仓库源码版本为 `1.0.9`，尚未发布。源码开发请使用检出副本：

```bash
git clone https://github.com/farfarfun/fartask.git
cd fartask
uv sync            # development environment (or: pip install .)
```

## 使用

在任务目录中调用 `submit_task()`。目录应包含 `config.slurm`（通过 `sbatch` 提交）或 `main.cpp`（使用 `g++` 编译并在本地运行）。安装 `fartask` 及提供 `g++` 的 C++ 编译器后，可运行以下本地 C++ 示例：

```bash
mkdir fartask-example
cd fartask-example
cat > main.cpp <<'EOF'
#include <cstdio>
int main() { std::puts("hello from fartask"); }
EOF

python - <<'PY'
from fartask import submit_task

task_dir = submit_task()
print(task_dir)
PY
```

`submit_task()` 会将任务文件复制到 `$HOME/workbench` 下按时间命名的目录中，在那里运行任务并返回该目录。当前目录既没有 `config.slurm` 也没有 `main.cpp` 时会抛出 `TaskSubmissionError`；提交、编译或执行以非零状态退出时会抛出 `TaskCommandError`。

SLURM 任务则在任务目录创建 `config.slurm`。提交需要可用的 `sbatch` 命令及目标 SLURM 集群的访问权限。

每次提交都会记录在本地 SQLite 数据库（`tasks.db`）中，包含状态（`pending`/`running`/`completed`/`failed`）及输出。可通过 `TaskManager` 查询或编辑这些记录：

```python
from fartask import TaskManager

manager = TaskManager()  # defaults to sqlite:///tasks.db
for task in manager.get_all_tasks():
    print(task.id, task.task_type, task.status)
```

使用已安装的 CLI 启动网页看板，以查看和管理任务：

```bash
fartask
```

该命令启动 NiceGUI 服务（默认 `http://0.0.0.0:8080`），列出全部任务，并可查看输出或删除任务。

长期运行的部署可安装当前检出版本或已发布版本，再管理这个已安装的看板进程：

```bash
scripts/setup.sh install-dev  # build and install this checkout
scripts/setup.sh start        # background
scripts/setup.sh run          # foreground
scripts/setup.sh status
scripts/setup.sh stop
```

生产主机应安装已发布版本。运行命令刻意不提供 `dev`/`prod` 参数；实际运行内容由当前安装的包决定。

```bash
git clone https://github.com/farfarfun/fartask.git
cd fartask
scripts/setup.sh install-prod 1.0.9
scripts/setup.sh start
```

## 迁移说明

`fartask.Task` 在 1.0.9 中作为已废弃的兼容类保留。它从未提交或管理任务，实例化时现在会发出 `DeprecationWarning`。请使用 `submit_task()` 提交任务，使用 `TaskManager` 查询或更新任务记录。`Task` 不会在 1.1 前移除，计划在 2.0.0 移除。

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
