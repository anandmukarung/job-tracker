from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, crud
from .database import engine, Base, get_db

#Create database tables if not already created
Base.metadata.create_all(bind=engine)

#Initialize app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Create a job
@app.post("/jobs/", response_model=schemas.Job)
def create_job_route(job: schemas.JobCreate, db: Session = Depends(get_db)):
    return crud.create_job(db=db, job=job)

#Return all jobs with pagination
@app.get("/jobs/", response_model=list[schemas.Job])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = crud.get_jobs(db, skip=skip, limit=limit)
    return jobs

#Search job by criteria
@app.get("/jobs/search", response_model=list[schemas.Job])
def search_jobs(
    company: str = None,  # type: ignore
    title: str = None,  # type: ignore
    location: str = None,  # type: ignore
    status: str = None,  # type: ignore
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
@app.get("/jobs/{job_id}", response_model=schemas.Job)
def read_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

#Delete a job
@app.delete("/jobs/{job_id}", response_model=schemas.Job)
def delete_job_route(job_id: int, db: Session = Depends(get_db)):
    db_job = crud.get_job_by_id(db, job_id)
    if not db_job:
        raise HTTPException(status_code=404, detail = "Job not found")
    return crud.delete_job(db=db, job_id=job_id)

#Update a job
@app.put("/jobs/{job_id}", response_model=schemas.Job)
def update_job(job_id: int, job_update: schemas.JobUpdate, db: Session = Depends(get_db)):
    job = crud.update_job(db=db, job_id=job_id,job_update=job_update)
    if not job:
        raise HTTPException(status_code=404, detail= "Job not found")
    return job

#Upload jobs in bulk
@app.post("/jobs/batch", response_model=list[schemas.Job])
def create_jobs_batch(jobs: list[schemas.JobCreate], db: Session = Depends(get_db)):
    created_jobs = []
    for job in jobs:
        created = crud.create_job(db=db, job=job)
        created_jobs.append(created)
    return created_jobs

@app.get("/")
def root():
    return {"message": "Job Tracker API is running with DB!"}

