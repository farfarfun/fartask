"""任务记录的 SQLAlchemy 模型与数据库会话管理。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Engine, Integer, String, Text, create_engine
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class TaskModel(Base):
    """任务记录表：一条记录对应一次 SLURM/C++ 任务提交。"""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_dir = Column(String(255), nullable=False)
    status = Column(
        String(50), default="pending"
    )  # 取值：pending（待处理）、running（运行中）、completed（已完成）、failed（失败）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    description = Column(Text, nullable=True)
    task_type = Column(String(50))  # 取值示例：slurm、cpp 等
    output = Column(Text, nullable=True)


_engine = None
_session_factory = None


def get_engine(db_path: str = "sqlite:///tasks.db") -> Engine:
    """获取（并按需惰性初始化）数据库引擎，避免在 import 时产生副作用。

    Args:
        db_path: 数据库连接串，默认在当前工作目录下的 tasks.db。

    Returns:
        SQLAlchemy Engine 实例。
    """
    global _engine
    if _engine is None:
        _engine = create_engine(db_path)
        Base.metadata.create_all(_engine)
    return _engine


def get_session_factory() -> sessionmaker:
    """获取（并按需惰性初始化）Session 工厂。

    Returns:
        SQLAlchemy sessionmaker 实例。
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory


def Session() -> SASession:  # noqa: N802 - 保持历史调用方式 Session() 兼容
    """创建一个新的数据库会话（惰性初始化引擎，import 时不产生副作用）。

    Returns:
        SQLAlchemy Session 实例。
    """
    return get_session_factory()()
