from pydantic import BaseModel 
from typing import Optional 
from datetime import date, datetime
from pydantic import ConfigDict

class JobBase(BaseModel):
    title: str
    company: str
    location: str
    job_description: Optional[str] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    resume_path: Optional[str] = None
    status : Optional[str] = "Applied"
    job_board_id: Optional[str] = None
    job_link: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    
class JobCreate(JobBase):
    pass

class JobUpdate(JobBase):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_description: Optional[str] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    resume_path: Optional[str] = None
    status : Optional[str] = None
    job_board_id: Optional[str] = None
    job_link: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    
class Job(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
