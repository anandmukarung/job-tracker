import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db
from .test_database import engine,override_get_db
from backend import models

# Override DB dependency to use in-memory DB
app.dependency_overrides[get_db] = override_get_db

# Create tables in memory
models.Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_create_job():
    response = client.post(
        "/jobs/",
        json={
            "title": "Software Engineer",
            "company": "DTN",
            "location": "Remote",
            "status": "applied",
            "applied_date": "2025-09-26",
            "job_description": "Test Job",
            "resume:path": None,
            "job_board_id": "12345",
            "source": "LinkedIn"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"]=="Software Engineer"
    assert data["job_board_id"] == "12345"

def test_read_jobs():
    response = client.get("/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_read_job():
    # Create first
    create_resp = client.post("/jobs/", json={
        "title": "QA Engineer",
        "company": "Amazon",
        "location": "Seattle, WA",
        "status": "applied",
        "applied_date": "2025-09-26",
        "job_description": "QA job",
        "resume_path": None,
        "job_board_id": "54321",
        "source": "Indeed"
    })
    job_id = create_resp.json()["id"]

    # Read
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Amazon"

def test_update_job():
    # Create
    create_resp = client.post("/jobs/", json={
        "title": "DevOps Engineer",
        "company": "Microsoft",
        "location": "Seattle, WA",
        "status": "applied",
        "applied_date": "2025-09-26",
        "job_description": "DevOps job",
        "resume_path": None,
        "job_board_id": "99999",
        "source": "LinkedIn"
    })
    job_id = create_resp.json()["id"]

    # Update status
    response = client.put(f"/jobs/{job_id}", json={"status": "rejected"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"

def test_delete_job():
    # Create
    create_resp = client.post("/jobs/", json={
        "title": "Backend Engineer",
        "company": "Facebook",
        "location": "San Jose, CA",
        "status": "applied",
        "applied_date": "2025-09-26",
        "job_description": "Backend job",
        "resume_path": None,
        "job_board_id": "88888",
        "source": "LinkedIn"
    })
    job_id = create_resp.json()["id"]

    # Delete
    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id

    # Verify deleted
    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 404

def test_search_jobs():
    # Create multiple jobs
    client.post("/jobs/", json={"title": "Backend Engineer", "company": "Google", "status": "applied", "location": "San Fransisco, CA", "applied_date": "2025-09-25", "job_description": "", "resume_path": None, "job_board_id": "111", "source": "LinkedIn"})
    client.post("/jobs/", json={"title": "Frontend Engineer", "company": "Google", "status": "applied", "location": "Pittsburgh", "applied_date": "2025-09-25", "job_description": "", "resume_path": None, "job_board_id": "222", "source": "LinkedIn"})
    client.post("/jobs/", json={"title": "DevOps Engineer I", "company": "Amazon", "status": "interview", "location": "Pittsburgh", "applied_date": "2025-09-26", "job_description": "", "resume_path": None, "job_board_id": "333", "source": "Indeed"})
    client.post("/jobs/", json={"title": "DevOps Engineer II", "company": "Amazon", "status": "applied", "location": "Seattle, WA", "applied_date": "2025-09-26", "job_description": "", "resume_path": None, "job_board_id": "333", "source": "Indeed"})

    # Search by company
    response = client.get("/jobs/search?company=Google")
    data = response.json()
    print(data)
    print(len(data))
    assert len(data) == 2

    # Search by title
    response = client.get("/jobs/search?title=DevOps")
    data = response.json()
    assert len(data) == 2
    assert data[0]["company"] == "Amazon"

    # Search by Status
    response = client.get("/jobs/search?status=interview")
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "DevOps Engineer I"

    # Search by Location
    response = client.get("/jobs/search?location=Pittsburgh&sort_desc=false")
    data = response.json()
    print(data)
    assert len(data) == 2
    assert data[0]["company"] == "Google"

    # Search with pagination
    response = client.get("/jobs/search?company=Google&skip=1&limit=1")
    data = response.json()
    assert len(data) == 1

def test_batch_jobs():

    old_data = client.get("/jobs/").json()

    client.post("/jobs/batch", json=[
        {"title": "Backend Engineer", "company": "Amazon", "status": "applied", "location": "San Fransisco, CA", "applied_date": "2025-09-29", "job_description": "", "resume_path": None, "job_board_id": None, "source": "LinkedIn"},
        {"title": "Frontend Engineer", "company": "Microsoft", "status": "applied", "location": "Pittsburgh", "applied_date": "2025-09-29", "job_description": "", "resume_path": None, "job_board_id": None, "source": "LinkedIn"},
        {"title": "DevOps Engineer I", "company": "Apple", "status": "interview", "location": "Pittsburgh", "applied_date": "2025-09-29", "job_description": "", "resume_path": None, "job_board_id": None, "source": "Indeed"},
        {"title": "DevOps Engineer II", "company": "Apple", "status": "applied", "location": "Seattle, WA", "applied_date": "2025-09-29", "job_description": "", "resume_path": None, "job_board_id": None, "source": "Indeed"},
    ])

    new_data = client.get("/jobs/").json()
    assert len(new_data) == (len(old_data) + 4)

