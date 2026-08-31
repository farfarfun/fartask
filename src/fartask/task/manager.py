from datetime import datetime

from ..models.task_model import Session, TaskModel


class TaskManager:
    """任务记录的增删改查管理器，封装对 `TaskModel` 表的数据库访问。"""

    def __init__(self) -> None:
        """创建一个新的数据库会话。"""
        self.session = Session()

    def create_task(
        self, task_dir: str, task_type: str, description: str | None = None
    ) -> TaskModel:
        """创建一条新的任务记录，初始状态为 pending。

        Args:
            task_dir: 任务工作目录。
            task_type: 任务类型（如 "slurm"、"cpp"）。
            description: 任务描述，可选。

        Returns:
            新创建的任务记录。
        """
        task = TaskModel(
            task_dir=task_dir,
            task_type=task_type,
            description=description,
            status="pending",
        )
        self.session.add(task)
        self.session.commit()
        return task

    def get_task(self, task_id: int) -> TaskModel | None:
        """按 ID 查询单条任务记录。

        Args:
            task_id: 任务 ID。

        Returns:
            找到则返回任务记录，否则返回 None。
        """
        return self.session.query(TaskModel).filter(TaskModel.id == task_id).first()

    def get_all_tasks(self) -> list[TaskModel]:
        """查询全部任务记录，按创建时间倒序排列。

        Returns:
            任务记录列表。
        """
        return self.session.query(TaskModel).order_by(TaskModel.created_at.desc()).all()

    def update_task_status(
        self, task_id: int, status: str, output: str | None = None
    ) -> TaskModel | None:
        """更新任务状态（及可选的输出内容）。

        Args:
            task_id: 任务 ID。
            status: 新状态（如 "running"、"completed"、"failed"）。
            output: 任务输出内容，可选。

        Returns:
            更新后的任务记录；任务不存在时返回 None。
        """
        task = self.get_task(task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now()
            if output:
                task.output = output
            self.session.commit()
        return task

    def delete_task(self, task_id: int) -> bool:
        """删除指定任务记录。

        Args:
            task_id: 任务 ID。

        Returns:
            删除成功返回 True，任务不存在返回 False。
        """
        task = self.get_task(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False

    def __del__(self) -> None:
        self.session.close()
