from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False, index=True)
    location: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    applied_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    job_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resume_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_board_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True, index=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
