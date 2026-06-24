import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func #tarih ataması

Base = declarative_base()

class JobStatus(str,enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead-letter"
    FROZEN = "frozen"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer,primary_key=True, index=True)
    status = Column(Enum(JobStatus),default=JobStatus.PENDING)
    payload = Column(JSON, nullable=False)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text,nullable=True)
    completed_at = Column(DateTime(timezone=True),nullable=True)

