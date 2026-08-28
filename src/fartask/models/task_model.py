from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_dir = Column(String(255), nullable=False)
    status = Column(
        String(50), default="pending"
    )  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    description = Column(Text, nullable=True)
    task_type = Column(String(50))  # slurm, cpp, etc.
    output = Column(Text, nullable=True)


# 创建数据库连接
engine = create_engine("sqlite:///tasks.db", echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
