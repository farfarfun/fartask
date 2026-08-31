# fartask

Task submission and tracking for SLURM cluster jobs and local C++ compile-and-run jobs, with a NiceGUI web dashboard for monitoring task status.

## Install

```bash
pip install fartask
```

## Usage

Submit a task from a directory containing either `config.slurm` (submitted via `sbatch`) or `main.cpp` (compiled with `g++` and executed locally):

```python
from fartask.task.submit import submit_task

submit_task()
```

Each submission is recorded in a local SQLite database (`tasks.db`) with its status (`pending`/`running`/`completed`/`failed`) and output.

Launch the web dashboard to view and manage tasks:

```bash
python -m fartask
```

This starts a NiceGUI server (default `http://0.0.0.0:8080`) listing all tasks with options to view output or delete a task.

For long-running deployments, use `scripts/setup.sh` to manage the dashboard process (`run`/`start`/`stop`/`restart` each require a `dev` or `prod` environment argument; `status` reports both):

```bash
scripts/setup.sh start prod   # background
scripts/setup.sh run dev      # foreground
scripts/setup.sh status
scripts/setup.sh stop prod
```

`prod` only runs an installed `fartask` package (via `pip install fartask`); it refuses to start from an editable source checkout.

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
