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
import shlex
import shutil
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

from farlog import getLogger
from funshell import run_shell

from .manager import TaskManager

logger = getLogger("fartask")

CommandRunner = Callable[[Sequence[str], str], str]

# funshell.run_shell 只接受 shell 字符串，且捕获输出时不会按退出码抛错。
# 让 shell 在 stdout 末尾回传退出码，调用方据此判定成败。
_EXIT_MARKER = "__fartask_exit_code__"


class TaskSubmissionError(ValueError):
    """当前目录不包含可提交的任务文件。"""


class TaskCommandError(RuntimeError):
    """外部命令以非零状态退出，或命令执行过程本身失败。"""

    def __init__(
        self, command: Sequence[str], returncode: int | None, output: str
    ) -> None:
        """记录失败命令的上下文。

        Args:
            command: 失败的命令参数序列。
            returncode: 命令退出码；无法取得时为 None。
            output: 命令的合并输出（stdout + stderr）。
        """
        self.command = list(command)
        self.returncode = returncode
        self.output = output
        super().__init__(
            f"命令执行失败（退出码 {returncode}）：{shlex.join(self.command)}\n{output}"
        )


def _run_command(command: Sequence[str], cwd: str) -> str:
    """用组织包 `funshell` 执行命令，保留参数转义、cwd、输出捕获与失败抛错语义。

    Args:
        command: 命令参数序列，内部用 `shlex.join` 转义后交给 shell，
            含空格或 shell 元字符的路径不会被拆开或二次解释。
        cwd: 命令的工作目录。

    Returns:
        命令的合并输出（stdout + stderr），已去除首尾空白。

    Raises:
        TaskCommandError: 命令退出码非零，或 funshell 未能正常执行命令。
    """
    command_line = (
        f"{shlex.join(command)} 2>&1; printf '%s%s' {shlex.quote(_EXIT_MARKER)} \"$?\""
    )
    raw = run_shell(command_line, printf=False, cwd=cwd)
    output, marker, code_text = raw.rpartition(_EXIT_MARKER)
    if not marker:
        # funshell 吞掉异常后只会返回 "run shell error: ..." 之类的字符串。
        raise TaskCommandError(command, None, raw.strip())
    try:
        returncode = int(code_text.strip())
    except ValueError:
        raise TaskCommandError(command, None, raw.strip()) from None
    output = output.strip()
    if returncode != 0:
        raise TaskCommandError(command, returncode, output)
    return output


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
