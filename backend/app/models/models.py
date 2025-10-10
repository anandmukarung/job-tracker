from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func
from ..db.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    status = Column(String, nullable=True, index=True)
    applied_date = Column(Date, nullable=True, index=True)
    follow_up_date = Column(Date, nullable=True)
    job_link = Column(String, nullable=True)
    job_description = Column(String, nullable=True)
    resume_path = Column(String, nullable=True)
    job_board_id = Column(String, unique=True,nullable=True, index=True)
    source = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))