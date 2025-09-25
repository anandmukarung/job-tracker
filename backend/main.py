from fastapi import FastAPI
from . import models, database

app = FastAPI()

#Create database tables
models.Base.metadata.create_all(bind=database.engine)

@app.get("/")
def root():
    return {"message": "Job Tracker API is running with DB!"}