from nicegui import ui
from ..task.manager import TaskManager
from ..task.submit import submit_task

task_manager = TaskManager()


def create_task_list():
    with ui.card().classes("w-full"):
        ui.label("任务列表").classes("text-h6")

        # 创建任务表格
        columns = [
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "task_dir", "label": "任务目录", "field": "task_dir"},
            {"name": "status", "label": "状态", "field": "status"},
            {"name": "task_type", "label": "任务类型", "field": "task_type"},
            {"name": "created_at", "label": "创建时间", "field": "created_at"},
            {"name": "description", "label": "描述", "field": "description"},
        ]

        tasks = task_manager.get_all_tasks()
        rows = [
            {
                "id": task.id,
                "task_dir": task.task_dir,
                "status": task.status,
                "task_type": task.task_type,
                "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "description": task.description,
            }
            for task in tasks
        ]

        table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        async def refresh_table():
            tasks = task_manager.get_all_tasks()
            rows = [
                {
                    "id": task.id,
                    "task_dir": task.task_dir,
                    "status": task.status,
                    "task_type": task.task_type,
                    "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": task.description,
                }
                for task in tasks
            ]
            table.rows = rows

        async def delete_task(task_id: int):
            if task_manager.delete_task(task_id):
                ui.notify(f"任务 {task_id} 已删除")
                await refresh_table()
            else:
                ui.notify(f"删除任务 {task_id} 失败", type="negative")

        async def view_task_output(task_id: int):
            task = task_manager.get_task(task_id)
            if task and task.output:
                with ui.dialog() as dialog, ui.card():
                    ui.label(f"任务 {task_id} 输出").classes("text-h6")
                    ui.textarea(value=task.output, readonly=True).classes("w-full")
                    ui.button("关闭", on_click=dialog.close)
                dialog.open()
            else:
                ui.notify("没有可用的输出", type="warning")

        # 添加操作按钮
        with ui.row():
            ui.button("刷新", on_click=refresh_table).classes("mr-2")
            for row in rows:
                with ui.row():
                    ui.button(
                        "查看输出", on_click=lambda r=row: view_task_output(r["id"])
                    ).classes("mr-2")
                    ui.button(
                        "删除", on_click=lambda r=row: delete_task(r["id"]), color="red"
                    )


@ui.page("/")
def main_page():
    ui.label("任务管理系统").classes("text-h4 q-mb-md")
    create_task_list()


def start_web_server(host="0.0.0.0", port=8080):
    ui.run(host=host, port=port, title="任务管理系统")
