from backend.app.main import app


def test_gmail_status_reports_missing_credentials(client, monkeypatch) -> None:
    monkeypatch.setattr("backend.app.routers.gmail.load_credentials", lambda: None)

    response = client.get("/gmail/status")

    assert response.status_code == 200
    assert response.json() == {"authorized": False, "message": "No credentials found."}


def test_gmail_status_reports_token_state(client, monkeypatch) -> None:
    class FakeCredentials:
        valid = False

    monkeypatch.setattr("backend.app.routers.gmail.load_credentials", lambda: FakeCredentials())
    monkeypatch.setattr("backend.app.routers.gmail.get_valid_credentials", lambda: FakeCredentials())

    response = client.get("/gmail/status")

    assert response.status_code == 200
    assert response.json() == {"authorized": True, "token_expired": True}


def test_gmail_status_reports_reauth_when_refresh_fails(client, monkeypatch) -> None:
    class FakeCredentials:
        valid = False

    monkeypatch.setattr("backend.app.routers.gmail.load_credentials", lambda: FakeCredentials())
    monkeypatch.setattr(
        "backend.app.routers.gmail.get_valid_credentials",
        lambda: (_ for _ in ()).throw(RuntimeError("invalid_grant")),
    )

    response = client.get("/gmail/status")

    assert response.status_code == 200
    assert response.json()["authorized"] is False
    assert response.json()["requires_reauth"] is True


def test_gmail_callback_alias_route_exists(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.routers.gmail.exchange_code_and_save_tokens",
        lambda code, redirect_uri: {"token": "new-token"},
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.resolve_redirect_uri",
        lambda uri: "http://localhost:8000/external/auth/callback",
    )

    response = client.get("/external/auth/callback?code=test-code")

    assert response.status_code == 200
    assert response.json()["message"] == "Authorization successful!"


def test_get_jobs_from_gmail_returns_results(client, monkeypatch) -> None:
    monkeypatch.setattr("backend.app.routers.gmail.crud.get_jobs", lambda db, skip, limit: [])
    monkeypatch.setattr(
        "backend.app.routers.gmail.fetch_job_applications_from_gmail",
        lambda query, max_results, existing_jobs: [
            {
                "gmail_message_id": "abc123",
                "thread_id": "thread-1",
                "from": "recruiter@company.com",
                "subject": "Interview update",
                "date": "2025-10-01T00:00:00Z",
                "source": "company_email",
                "email_content": {
                    "snippet": "We would like to schedule an interview.",
                    "body_text": "We would like to schedule an interview for the Product Manager position.",
                    "from_email": "recruiter@company.com",
                    "from_domain": "company.com",
                },
                "classification": {
                    "label": "INTERVIEW",
                    "confidence": 0.95,
                    "reasons": ["interview_phrase:interview scheduled"],
                },
                "job_draft": None,
                "update_items": {
                    "status": "Interview",
                    "follow_up_date": "2025-10-01",
                    "job_link": "https://example.com/job/1",
                    "company": "Company",
                    "title": "Product Manager",
                    "notes": "Imported from Gmail update. Review before applying to an existing job.",
                    "gmail_thread_id": "thread-1",
                },
                "extraction_candidates": {
                    "title": [{"value": "Product Manager", "confidence": 0.9, "source": "application_phrase"}],
                    "company": [{"value": "Company", "confidence": 0.8, "source": "sender"}],
                    "location": [],
                    "identifiers": {
                        "gmail_thread_id": [{"value": "thread-1", "confidence": 1.0, "source": "gmail_thread"}],
                    },
                },
                "match_candidates": [],
                "best_match": None,
                "needs_review": True,
            }
        ],
    )

    response = client.get("/gmail/jobs?query=interview&max_results=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["jobs"][0]["classification"]["label"] == "INTERVIEW"
    assert payload["jobs"][0]["email_content"]["body_text"].startswith("We would like to schedule")
    assert payload["jobs"][0]["job_draft"] is None
    assert payload["jobs"][0]["update_items"]["status"] == "Interview"


def test_get_jobs_from_gmail_handles_service_errors(client, monkeypatch) -> None:
    monkeypatch.setattr("backend.app.routers.gmail.crud.get_jobs", lambda db, skip, limit: [])
    monkeypatch.setattr(
        "backend.app.routers.gmail.fetch_job_applications_from_gmail",
        lambda query, max_results, existing_jobs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = client.get("/gmail/jobs")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch Gmail jobs: boom"
