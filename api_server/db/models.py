# api_server/db/models.py

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Run(Base):
    """Run tracking model for touchpoint executions."""

    __tablename__ = "runs"

    run_id = Column(String, primary_key=True)  # UUID
    handle = Column(String, nullable=False, index=True)
    touchpoint_type = Column(String, nullable=False)  # "profile_enrich", "connect", "message", etc.
    touchpoint_input = Column(JSON, nullable=False)  # Full touchpoint payload
    status = Column(String, nullable=False, index=True)  # "pending", "running", "completed", "failed"
    result = Column(JSON, nullable=True)  # Touchpoint output/result
    error = Column(Text, nullable=True)  # Error message if failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=True)  # Optional tags for filtering
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)


class Schedule(Base):
    """Schedule model for recurring touchpoint executions."""

    __tablename__ = "schedules"

    schedule_id = Column(String, primary_key=True)  # UUID
    handle = Column(String, nullable=False, index=True)
    touchpoint_type = Column(String, nullable=False)
    touchpoint_input = Column(JSON, nullable=False)  # Full touchpoint payload
    cron = Column(String, nullable=False)  # Cron expression
    next_run_at = Column(DateTime, nullable=True, index=True)  # Next scheduled execution time
    active = Column(Boolean, default=True, nullable=False)  # True if active, False if paused
    tags = Column(JSON, nullable=True)  # Optional tags for filtering
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
