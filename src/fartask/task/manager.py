from datetime import datetime
from typing import List, Optional
from ..models.task_model import TaskModel, Session


class TaskManager:
    def __init__(self):
        self.session = Session()

    def create_task(
        self, task_dir: str, task_type: str, description: Optional[str] = None
    ) -> TaskModel:
        task = TaskModel(
            task_dir=task_dir,
            task_type=task_type,
            description=description,
            status="pending",
        )
        self.session.add(task)
        self.session.commit()
        return task

    def get_task(self, task_id: int) -> Optional[TaskModel]:
        return self.session.query(TaskModel).filter(TaskModel.id == task_id).first()

    def get_all_tasks(self) -> List[TaskModel]:
        return self.session.query(TaskModel).order_by(TaskModel.created_at.desc()).all()

    def update_task_status(
        self, task_id: int, status: str, output: Optional[str] = None
    ) -> Optional[TaskModel]:
        task = self.get_task(task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now()
            if output:
                task.output = output
            self.session.commit()
        return task

    def delete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False

    def __del__(self):
        self.session.close()
