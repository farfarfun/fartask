# fartask

Task submission and tracking for SLURM cluster jobs and local C++ compile-and-run jobs, with a NiceGUI web dashboard for monitoring task status.

## Install

`fartask` is not published on PyPI yet, so install it from the source checkout:

```bash
git clone https://github.com/farfarfun/fartask.git
cd fartask
uv sync            # development environment (or: pip install .)
```

## Usage

Submit a task from a directory containing either `config.slurm` (submitted via `sbatch`) or `main.cpp` (compiled with `g++` and executed locally):

```python
from fartask import submit_task

task_dir = submit_task()
```

`submit_task()` copies the job files into a timestamped directory under `$HOME/workbench`, runs the job there, and returns that directory. It raises `TaskSubmissionError` when the current directory contains neither `config.slurm` nor `main.cpp`, and `TaskCommandError` when submission, compilation or execution exits non-zero.

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

For long-running deployments, use `scripts/setup.sh` to manage the dashboard process (`run`/`start`/`stop`/`restart` each require a `dev` or `prod` environment argument; `status` reports both):

```bash
scripts/setup.sh start dev    # background
scripts/setup.sh run dev      # foreground
scripts/setup.sh status
scripts/setup.sh stop dev
```

`prod` only runs a `fartask` distribution installed from a package index; it refuses to start from an editable or locally built checkout. Since the package is not on PyPI yet, use `dev` for now — `prod` becomes available once a release is published.

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
