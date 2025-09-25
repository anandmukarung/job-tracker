from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Job Tracker API is running!"}