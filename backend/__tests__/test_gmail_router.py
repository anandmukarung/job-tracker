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
    monkeypatch.setattr(
        "backend.app.routers.gmail.fetch_job_applications_from_gmail",
        lambda query, max_results: [{"subject": "Interview update", "from": "recruiter@company.com"}],
    )

    response = client.get("/gmail/jobs?query=interview&max_results=5")

    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "jobs": [{"subject": "Interview update", "from": "recruiter@company.com"}],
    }


def test_get_jobs_from_gmail_handles_service_errors(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.routers.gmail.fetch_job_applications_from_gmail",
        lambda query, max_results: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = client.get("/gmail/jobs")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch Gmail jobs: boom"
