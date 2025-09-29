from sqlalchemy.orm import Session
from . import models, schemas

def create_job(db: Session, job: schemas.JobCreate):
    #Check for duplicate job posting
    if job.job_board_id and job.company:
        existing_job = db.query(models.Job).filter(
            models.Job.job_board_id == job.job_board_id,
            models.Job.company == job.company
        ).first()
        if existing_job:
            return existing_job # Return existing job instead of duplicating
    #Create new job instance
    db_job = models.Job(
        title=job.title,
        company=job.company,
        location=job.location,
        status=job.status,
        applied_date=job.applied_date,
        follow_up_date=job.follow_up_date,
        job_link=job.job_link,
        job_description=job.description,
        resume_path=job.resume_path,
        job_board_id=job.job_board_id,
        source=job.source,
        notes=job.notes
    )
    
    #Add to session and commit
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job_by_id(db: Session, job_id: int):
    return db.query(models.Job).filter(models.Job.id == job_id).first()

def get_jobs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Job).offset(skip).limit(limit).all()

def update_job(db: Session, job_id: int, job_update: schemas.JobUpdate):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        return None
    #Update fields if provided
    update_data = job_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_job, key, value)
    db.commit()
    db.refresh(db_job)
    return db_job

def delete_job(db: Session, job_id: int):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        return None
    db.delete(db_job)
    db.commit()
    return db_job

#Search job by company, title, location or status
def get_jobs_by_filters(
    db: Session, 
    company: str = None, # type: ignore
    title: str = None, # type: ignore
    location: str = None, # type: ignore
    status: str = None, # type: ignore
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "applied_date",
    sort_desc: bool = True
): 
    query = db.query(models.Job)
    if company:
        query = query.filter(models.Job.company.ilike(f"%{company}%"))
    if title:
        query = query.filter(models.Job.title.ilike(f"%{title}%"))
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if status:
        query = query.filter(models.Job.status.ilike(f"%{status}%"))

    #Sorting
    if hasattr(models.Job, sort_by):
        column = getattr(models.Job, sort_by)
        if sort_desc: 
            column = column.desc()
        query = query.order_by(column)
    return query.offset(skip).limit(limit).all()