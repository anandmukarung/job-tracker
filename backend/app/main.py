from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .db.database import Base, engine
from .routers import jobs, gmail

#Create database tables if not already created
Base.metadata.create_all(bind=engine)

#Initialize app
app = FastAPI(title="Job Applications Tracker API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Register Routers
app.include_router(jobs.router)
app.include_router(gmail.router)

@app.get("/")
def root():
    return {"message": "Job Tracker API is running with DB!"}


