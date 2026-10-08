# fartask

Task submission and tracking for SLURM cluster jobs and local C++ compile-and-run jobs, with a NiceGUI web dashboard for monitoring task status.

## Install

```bash
pip install fartask
```

`fartask` 1.0.8 is available on PyPI. For source development, use a checkout instead:

```bash
git clone https://github.com/farfarfun/fartask.git
cd fartask
uv sync            # development environment (or: pip install .)
```

## Usage

Run `submit_task()` inside a task directory containing either `config.slurm` (submitted via `sbatch`) or `main.cpp` (compiled with `g++` and executed locally). The following local C++ example is runnable after installing `fartask` and a C++ compiler that provides `g++`:

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

`submit_task()` copies the job files into a timestamped directory under `$HOME/workbench`, runs the job there, and returns that directory. It raises `TaskSubmissionError` when the current directory contains neither `config.slurm` nor `main.cpp`, and `TaskCommandError` when submission, compilation or execution exits non-zero.

For a SLURM task, create `config.slurm` in the task directory instead. Its submission requires an available `sbatch` command and access to the target SLURM cluster.

Each submission is recorded in a local SQLite database (`tasks.db`) with its status (`pending`/`running`/`completed`/`failed`) and output. Query or edit those records with `TaskManager`:

```python
from fartask import TaskManager

manager = TaskManager()  # defaults to sqlite:///tasks.db
for task in manager.get_all_tasks():
    print(task.id, task.task_type, task.status)
```

Launch the web dashboard to view and manage tasks:

```bash
python -m fartask
```

This starts a NiceGUI server (default `http://0.0.0.0:8080`) listing all tasks with options to view output or delete a task.

For long-running deployments, install either the current checkout or a published version, then manage the one installed dashboard process:

```bash
scripts/setup.sh install-dev  # build and install this checkout
scripts/setup.sh start        # background
scripts/setup.sh run          # foreground
scripts/setup.sh status
scripts/setup.sh stop
```

For a production host, install a published version instead. Runtime commands intentionally have no `dev`/`prod` argument; the currently installed package determines what runs.

```bash
git clone https://github.com/farfarfun/fartask.git
cd fartask
scripts/setup.sh install-prod 1.0.9
scripts/setup.sh start
```

## Migration

`fartask.Task` is retained as a deprecated compatibility class in 1.0.9. It never submitted or managed tasks and now emits a `DeprecationWarning` when instantiated. Use `submit_task()` to submit work and `TaskManager` to query or update task records. `Task` will not be removed before 1.1 and is planned for removal in 2.0.0.

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
