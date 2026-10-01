"""SLURM 集群任务 / 本地 C++ 编译运行任务的提交入口。

对应的手工提交流程（供参考）：

    #!/bin/bash
    task_root='/work/home/liuc12/workbench'
    timestamp=$(date +"%Y%m%d%H%M%S")
    task_dir="$task_root/task_$timestamp"

    mkdir "$task_dir"
    cp -r *.cpp *.h *.sh *.slurm *.f90 *.dat  $task_dir 2>/dev/null
    cd "$task_dir"
    pwd
    sbatch config.slurm
"""

import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

from farlog import getLogger

from .manager import TaskManager

logger = getLogger("fartask")

CommandRunner = Callable[[Sequence[str], str], str]


class TaskSubmissionError(ValueError):
    """当前目录不包含可提交的任务文件。"""


def _run_command(command: Sequence[str], cwd: str) -> str:
    result = subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def submit_task(command_runner: CommandRunner = _run_command) -> str:
    """提交当前目录下的任务：优先 SLURM（config.slurm），否则本地编译运行（main.cpp）。

    Args:
        command_runner: 接收命令参数序列和工作目录的命令执行器。

    Returns:
        本次提交使用的任务目录。
    """
    source_dir = Path.cwd()
    slurm_file = source_dir / "config.slurm"
    cpp_file = source_dir / "main.cpp"
    if not slurm_file.exists() and not cpp_file.exists():
        raise TaskSubmissionError(
            f"No config.slurm or main.cpp found in task directory: {source_dir}"
        )

    task_dir = os.path.join(
        os.environ["HOME"],
        "workbench",
        datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    )
    logger.info(f"任务主目录：{task_dir}")
    os.makedirs(task_dir, exist_ok=True)

    # 创建任务管理器实例
    task_manager = TaskManager()
    task_type = None
    description = None

    logger.info(f"step1: 复制文件到任务主目录：{task_dir}")
    for pattern in ("*.cpp", "*.h", "*.sh", "*.slurm", "*.f90", "*.dat"):
        for source in source_dir.glob(pattern):
            destination = Path(task_dir) / source.name
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)

    try:
        if slurm_file.exists():
            task_type = "slurm"
            description = "SLURM cluster task"
            logger.info("step2: 检测到config.slurm文件，提交任务")
            # 创建任务记录
            task = task_manager.create_task(task_dir, task_type, description)

            try:
                output = command_runner(["sbatch", "config.slurm"], task_dir)
                task_manager.update_task_status(task.id, "running", output)
            except Exception as e:
                task_manager.update_task_status(task.id, "failed", str(e))
                raise

        else:
            task_type = "cpp"
            description = "Local C++ compilation and execution"
            # 创建任务记录
            task = task_manager.create_task(task_dir, task_type, description)

            try:
                logger.info("step2: 检测到main.cpp文件，编译")
                compile_output = command_runner(
                    ["g++", "main.cpp", "-o", "task.app"], task_dir
                )
                logger.info("step3: 编译完成，开始执行")
                execution_output = command_runner(["./task.app"], task_dir)
                task_manager.update_task_status(
                    task.id,
                    "completed",
                    f"Compilation: {compile_output}\nExecution: {execution_output}",
                )
            except Exception as e:
                task_manager.update_task_status(task.id, "failed", str(e))
                raise

        logger.info("任务提交完成")
        return task_dir
    except Exception as e:
        logger.error(f"任务执行失败: {e!s}")
        raise


if __name__ == "__main__":
    submit_task()
