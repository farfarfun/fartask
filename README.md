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
