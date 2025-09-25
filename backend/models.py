from sqlalchemy import Column, Integer, String, Date
from .database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    location = Column(String)
    application_date = Column(Date)
    status = Column(String)
    notes = Column(String)
    follow_up_date = Column(Date)
    job_link = Column(String)