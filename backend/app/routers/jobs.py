from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from ..db.database import get_db
from ..crud import crud
from ..schemas import schemas
from ..models import models

router = APIRouter(prefix="/jobs", tags=["Jobs"])

#Create a job
@router.post("/", response_model=schemas.Job)
def create_job_route(job: schemas.JobCreate, db: Session = Depends(get_db)):
    return crud.create_job(db=db, job=job)

#Return all jobs with pagination
@router.get("/", response_model=list[schemas.Job])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = crud.get_jobs(db, skip=skip, limit=limit)
    return jobs

#Search job by criteria
@router.get("/search", response_model=list[schemas.Job])
def search_jobs(
    company: Optional[str] = None,
    title: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "applied_date",
    sort_desc: bool = True,
    db: Session = Depends(get_db)): 
    if not hasattr(models.Job, sort_by):
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_by}")
    return crud.get_jobs_by_filters(
        db=db, 
        company=company, 
        title=title, 
        location=location, 
        status=status,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_desc=sort_desc
    )

#Get single job
@router.get("/{job_id}", response_model=schemas.Job)
def read_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

#Delete a job
@router.delete("/{job_id}", response_model=schemas.Job)
def delete_job_route(job_id: int, db: Session = Depends(get_db)):
    db_job = crud.get_job_by_id(db, job_id)
    if not db_job:
        raise HTTPException(status_code=404, detail = "Job not found")
    return crud.delete_job(db=db, job_id=job_id)

#Update a job
@router.put("/{job_id}", response_model=schemas.Job)
def update_job(job_id: int, job_update: schemas.JobUpdate, db: Session = Depends(get_db)):
    job = crud.update_job(db=db, job_id=job_id,job_update=job_update)
    if not job:
        raise HTTPException(status_code=404, detail= "Job not found")
    return job

#Upload jobs in bulk
@router.post("/batch", response_model=list[schemas.Job])
def create_jobs_batch(jobs: list[schemas.JobCreate], db: Session = Depends(get_db)):
    created_jobs = []
    for job in jobs:
        created = crud.create_job(db=db, job=job)
        created_jobs.append(created)
    return created_jobs
