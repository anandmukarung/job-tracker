def create_job_payload(**overrides):
    payload = {
        "title": "Software Engineer",
        "company": "OpenAI",
        "location": "Remote",
        "status": "Applied",
        "applied_date": "2025-09-26",
        "job_description": "Test job",
        "resume_path": None,
        "job_board_id": "openai-1",
        "source": "LinkedIn",
        "job_link": "https://example.com/job",
        "notes": "Referral submitted",
    }
    payload.update(overrides)
    return payload


def test_root_returns_health_message(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Job Tracker API is running with DB!"}


def test_create_job_returns_created_record(client):
    response = client.post("/jobs/", json=create_job_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Software Engineer"
    assert data["job_board_id"] == "openai-1"
    assert data["job_description"] == "Test job"


def test_create_job_reuses_existing_duplicate_by_company_and_job_board_id(client):
    payload = create_job_payload()

    first = client.post("/jobs/", json=payload)
    second = client.post("/jobs/", json=payload)
    jobs = client.get("/jobs/")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(jobs.json()) == 1


def test_read_single_job_returns_404_when_missing(client):
    response = client.get("/jobs/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_update_job_changes_status_and_description(client):
    create_resp = client.post("/jobs/", json=create_job_payload())
    job_id = create_resp.json()["id"]

    response = client.put(
        f"/jobs/{job_id}",
        json={"status": "Rejected", "job_description": "Role closed"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Rejected"
    assert data["job_description"] == "Role closed"


def test_update_missing_job_returns_404(client):
    response = client.put("/jobs/999", json={"status": "Rejected"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_delete_job_removes_record(client):
    create_resp = client.post(
        "/jobs/",
        json=create_job_payload(job_board_id="openai-delete"),
    )
    job_id = create_resp.json()["id"]

    response = client.delete(f"/jobs/{job_id}")
    get_resp = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert get_resp.status_code == 404


def test_delete_missing_job_returns_404(client):
    response = client.delete("/jobs/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_search_jobs_filters_and_sorts_results(client):
    client.post(
        "/jobs/",
        json=create_job_payload(
            title="Backend Engineer",
            company="Google",
            location="San Francisco, CA",
            status="Applied",
            applied_date="2025-09-25",
            job_board_id="google-1",
        ),
    )
    client.post(
        "/jobs/",
        json=create_job_payload(
            title="Frontend Engineer",
            company="Google",
            location="Pittsburgh",
            status="Applied",
            applied_date="2025-09-24",
            job_board_id="google-2",
        ),
    )
    client.post(
        "/jobs/",
        json=create_job_payload(
            title="DevOps Engineer I",
            company="Amazon",
            location="Pittsburgh",
            status="Interview",
            applied_date="2025-09-26",
            job_board_id="amazon-1",
        ),
    )
    client.post(
        "/jobs/",
        json=create_job_payload(
            title="DevOps Engineer II",
            company="Amazon",
            location="Seattle, WA",
            status="Applied",
            applied_date="2025-09-27",
            job_board_id="amazon-2",
        ),
    )

    company_response = client.get("/jobs/search?company=Google")
    title_response = client.get("/jobs/search?title=DevOps")
    status_response = client.get("/jobs/search?status=Interview")
    location_response = client.get("/jobs/search?location=Pittsburgh&sort_desc=false")
    paginated_response = client.get("/jobs/search?company=Google&skip=1&limit=1")

    assert len(company_response.json()) == 2
    assert len(title_response.json()) == 2
    assert title_response.json()[0]["title"] == "DevOps Engineer II"
    assert len(status_response.json()) == 1
    assert status_response.json()[0]["title"] == "DevOps Engineer I"
    assert [job["title"] for job in location_response.json()] == [
        "Frontend Engineer",
        "DevOps Engineer I",
    ]
    assert len(paginated_response.json()) == 1


def test_search_jobs_rejects_invalid_sort_field(client):
    response = client.get("/jobs/search?sort_by=not_a_field")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid sort field: not_a_field"


def test_batch_jobs_creates_all_records(client):
    payload = [
        create_job_payload(
            title="Backend Engineer",
            company="Amazon",
            location="San Francisco, CA",
            applied_date="2025-09-29",
            job_board_id="batch-1",
        ),
        create_job_payload(
            title="Frontend Engineer",
            company="Microsoft",
            location="Pittsburgh",
            applied_date="2025-09-29",
            job_board_id="batch-2",
        ),
        create_job_payload(
            title="DevOps Engineer I",
            company="Apple",
            location="Pittsburgh",
            status="Interview",
            applied_date="2025-09-29",
            job_board_id="batch-3",
        ),
        create_job_payload(
            title="DevOps Engineer II",
            company="Apple",
            location="Seattle, WA",
            applied_date="2025-09-29",
            job_board_id="batch-4",
        ),
    ]

    response = client.post("/jobs/batch", json=payload)
    jobs = client.get("/jobs/")

    assert response.status_code == 200
    assert len(response.json()) == 4
    assert len(jobs.json()) == 4
