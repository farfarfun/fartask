"""
#!/bin/bash
task_root='/work/home/liuc12/workbench'
timestamp=$(date +"%Y%m%d%H%M%S")
task_dir="$task_root/task_$timestamp"

mkdir "$task_dir"
cp -r *.cpp *.h *.sh *.slurm *.f90 *.dat  $task_dir 2>/dev/null
cd "$task_dir"
pwd
#ls -al
sbatch config.slurm
"""

import os
from datetime import datetime

from funshell import run_shell
from nltlog import getLogger

from .manager import TaskManager

logger = getLogger("nlttask")


def submit_task():
    task_dir = os.path.join(
        os.environ["HOME"], "/workbench", datetime.now().strftime("%Y%m%d%H%M%S")
    )
    logger.info(f"任务主目录：{task_dir}")
    os.makedirs(task_dir, exist_ok=True)

    # 创建任务管理器实例
    task_manager = TaskManager()
    task_type = None
    description = None

    logger.info(f"step1: 复制文件到任务主目录：{task_dir}")
    run_shell(f"cp -r *.cpp *.h *.sh *.slurm *.f90 *.dat {task_dir} 2>/dev/null")

    try:
        if os.path.exists("config.slurm"):
            task_type = "slurm"
            description = "SLURM cluster task"
            logger.info("step2: 检测到config.slurm文件，提交任务")
            # 创建任务记录
            task = task_manager.create_task(task_dir, task_type, description)

            try:
                output = run_shell(f"cd {task_dir} && sbatch config.slurm")
                task_manager.update_task_status(task.id, "running", output)
            except Exception as e:
                task_manager.update_task_status(task.id, "failed", str(e))
                raise e

        elif os.path.exists("main.cpp"):
            task_type = "cpp"
            description = "Local C++ compilation and execution"
            # 创建任务记录
            task = task_manager.create_task(task_dir, task_type, description)

            try:
                logger.info("step2: 检测到main.cpp文件，编译")
                compile_output = run_shell(f"cd {task_dir} && g++ main.cpp -o task.app")
                logger.info("step3: 编译完成，开始执行")
                execution_output = run_shell(f"cd {task_dir} && ./task.app")
                task_manager.update_task_status(
                    task.id,
                    "completed",
                    f"Compilation: {compile_output}\nExecution: {execution_output}",
                )
            except Exception as e:
                task_manager.update_task_status(task.id, "failed", str(e))
                raise e

        logger.info("任务提交完成")
        return task_dir
    except Exception as e:
        logger.error(f"任务执行失败: {str(e)}")
        raise e


if __name__ == "__main__":
    submit_task()
