from backend.app.main import app
from backend.app.routers import gmail as gmail_router
from backend.app.schemas.schemas import GmailParsedMessageReview
from backend.__tests__.conftest import TestingSessionLocal


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


def test_gmail_callback_redirects_to_frontend_when_state_present(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.routers.gmail.exchange_code_and_save_tokens",
        lambda code, redirect_uri: {"token": "new-token"},
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.resolve_redirect_uri",
        lambda uri: "http://localhost:8000/external/auth/callback",
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail._decode_oauth_state",
        lambda state: "http://127.0.0.1:5173/jobs",
    )

    response = client.get("/external/auth/callback?code=test-code&state=abc", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "http://127.0.0.1:5173/jobs?gmail=connected"


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


def test_preview_gmail_import_creates_session_and_marks_existing_items(client, db_session, monkeypatch) -> None:
    from backend.app.crud import crud
    from backend.app.models import models
    from datetime import date

    new_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "new-message",
            "thread_id": "thread-1",
            "from": "recruiter@company.com",
            "subject": "Application received",
            "date": "2025-01-15T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Thank you for applying.",
                "body_text": "Thank you for applying for the Backend Engineer position.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
            "job_draft": {
                "title": "Backend Engineer",
                "company": "Company",
                "location": "Remote",
                "applied_date": "2025-01-15",
                "status": "Applied",
                "source": "Gmail",
            },
            "update_items": None,
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "already_processed": False,
            "needs_review": True,
        }
    )
    existing_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "existing-message",
            "thread_id": "thread-2",
            "from": "recruiter@company.com",
            "subject": "Application update",
            "date": "2025-01-16T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Update on your application.",
                "body_text": "Update on your application.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "APPLICATION_UPDATE", "confidence": 0.9, "reasons": ["update"]},
            "job_draft": None,
            "update_items": {
                "status": "Interview",
                "follow_up_date": "2025-01-16",
                "company": "Company",
                "title": "Backend Engineer",
            },
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "already_processed": False,
            "needs_review": True,
        }
    )
    monkeypatch.setattr("backend.app.routers.gmail.get_gmail_service", lambda: object())
    monkeypatch.setattr(
        "backend.app.routers.gmail.list_message_ids_with_service",
        lambda service, q, max_results: ["new-message", "existing-message"],
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.get_message_with_service",
        lambda service, message_id: {"id": message_id, "threadId": "thread-1"}
        if message_id == "new-message"
        else (_ for _ in ()).throw(AssertionError("cached message should not be fetched again")),
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.get_message_metadata_with_service",
        lambda service, message_id: {
            "id": message_id,
            "snippet": "Thank you for applying." if message_id == "new-message" else "Update on your application.",
            "payload": {
                "headers": [
                    {"name": "From", "value": "recruiter@company.com"},
                    {"name": "Subject", "value": "Application received" if message_id == "new-message" else "Application update"},
                ]
            },
        },
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.parse_gmail_message",
        lambda message, existing_jobs: new_review if message["id"] == "new-message" else existing_review,
    )
    monkeypatch.setattr(
        gmail_router,
        "launch_gmail_preview_job",
        lambda session_id, start_date, end_date: gmail_router._run_gmail_preview_job(session_id, start_date, end_date),
    )
    monkeypatch.setattr(gmail_router, "_session_factory", lambda: TestingSessionLocal)

    session = crud.create_gmail_import_session(db_session, start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
    db_session.add(
        models.GmailImportItem(
            session_id=session.id,
            gmail_message_id="existing-message",
            gmail_thread_id="thread-2",
            from_email="recruiter@company.com",
            subject="Application update",
            payload_json=existing_review.model_dump_json(by_alias=True),
            selected_action="update",
            import_status="imported",
        )
    )
    db_session.commit()

    start_response = client.post("/gmail/import/preview?start_date=2025-01-01&end_date=2025-01-31")

    assert start_response.status_code == 200
    preview_session_id = start_response.json()["session"]["id"]

    response = client.get(f"/gmail/import/preview/{preview_session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["session"]["status"] == "completed"
    assert payload["session"]["new_items"] == 1
    new_item = next(item for item in payload["jobs"] if item["gmail_message_id"] == "new-message")
    existing_item = next(item for item in payload["jobs"] if item["gmail_message_id"] == "existing-message")
    assert new_item["already_processed"] is False
    assert existing_item["already_processed"] is True
    assert existing_item["import_status"] == "imported"


def test_preview_gmail_import_handles_service_errors(client, monkeypatch) -> None:
    def fail_preview_job(session_id: int, start_date, end_date) -> None:
        db = gmail_router._session_factory()()
        try:
            session = gmail_router.crud.get_gmail_import_session(db, session_id)
            assert session is not None
            gmail_router.crud.update_gmail_import_session(
                db,
                session,
                status="failed",
                preview_payload=[],
                error_message="Failed to fetch Gmail import preview: gmail unreachable",
            )
        finally:
            db.close()

    monkeypatch.setattr(gmail_router, "launch_gmail_preview_job", fail_preview_job)
    monkeypatch.setattr(gmail_router, "_session_factory", lambda: TestingSessionLocal)

    start_response = client.post("/gmail/import/preview?start_date=2025-01-01&end_date=2025-01-31")
    assert start_response.status_code == 200
    preview_session_id = start_response.json()["session"]["id"]

    response = client.get(f"/gmail/import/preview/{preview_session_id}")

    assert response.status_code == 200
    assert response.json()["session"]["status"] == "failed"
    assert response.json()["session"]["error_message"] == "Failed to fetch Gmail import preview: gmail unreachable"


def test_preview_gmail_import_deduplicates_duplicate_message_ids(client, monkeypatch) -> None:
    review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "duplicate-message",
            "thread_id": "thread-duplicate",
            "from": "recruiter@company.com",
            "subject": "Application received",
            "date": "2025-01-15T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Thank you for applying.",
                "body_text": "Thank you for applying for the Backend Engineer position.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
            "job_draft": {
                "title": "Backend Engineer",
                "company": "Company",
                "location": "Remote",
                "applied_date": "2025-01-15",
                "status": "Applied",
                "source": "Gmail",
            },
            "update_items": None,
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "already_processed": False,
            "needs_review": True,
        }
    )

    monkeypatch.setattr("backend.app.routers.gmail.get_gmail_service", lambda: object())
    monkeypatch.setattr(
        "backend.app.routers.gmail.list_message_ids_with_service",
        lambda service, q, max_results: ["duplicate-message", "duplicate-message"],
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.get_message_metadata_with_service",
        lambda service, message_id: {
            "id": message_id,
            "snippet": "Thank you for applying.",
            "payload": {
                "headers": [
                    {"name": "From", "value": "recruiter@company.com"},
                    {"name": "Subject", "value": "Application received"},
                ]
            },
        },
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.get_message_with_service",
        lambda service, message_id: {"id": message_id, "threadId": "thread-duplicate"},
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.parse_gmail_message",
        lambda message, existing_jobs: review,
    )
    monkeypatch.setattr(
        gmail_router,
        "launch_gmail_preview_job",
        lambda session_id, start_date, end_date: gmail_router._run_gmail_preview_job(session_id, start_date, end_date),
    )
    monkeypatch.setattr(gmail_router, "_session_factory", lambda: TestingSessionLocal)

    start_response = client.post("/gmail/import/preview?start_date=2025-01-01&end_date=2025-01-31")

    assert start_response.status_code == 200
    preview_session_id = start_response.json()["session"]["id"]

    response = client.get(f"/gmail/import/preview/{preview_session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["status"] == "completed"
    assert payload["count"] == 1
    assert payload["session"]["new_items"] == 1


def test_preview_gmail_import_reuses_fully_covered_overlapping_cache(client, db_session) -> None:
    from backend.app.crud import crud
    from datetime import date

    cached_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "cached-message",
            "thread_id": "thread-cached",
            "from": "recruiter@company.com",
            "subject": "Application received",
            "date": "2025-04-15T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Thank you for applying.",
                "body_text": "Thank you for applying for the Backend Engineer position.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
            "job_draft": {
                "title": "Backend Engineer",
                "company": "Company",
                "location": "Remote",
                "applied_date": "2025-04-15",
                "status": "Applied",
                "source": "Gmail",
            },
            "update_items": None,
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "needs_review": True,
        }
    )
    cached_session = crud.create_gmail_import_session(
        db_session,
        start_date=date(2025, 4, 1),
        end_date=date(2025, 5, 1),
    )
    crud.update_gmail_import_session(
        db_session,
        cached_session,
        status="completed",
        total_emails=1,
        new_items=0,
        cached_items=1,
        cache_hit=True,
        preview_payload=[cached_review],
        error_message=None,
    )

    response = client.post("/gmail/import/preview?start_date=2025-04-15&end_date=2025-05-01")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["status"] == "completed"
    assert payload["session"]["cache_hit"] is True
    preview_response = client.get(f"/gmail/import/preview/{payload['session']['id']}")
    assert preview_response.status_code == 200
    assert preview_response.json()["count"] == 1


def test_preview_hides_imported_and_skipped_items_unless_linked_job_was_deleted(client, db_session) -> None:
    from backend.app.crud import crud
    from backend.app.models import models
    from backend.app.schemas import schemas
    from datetime import date

    created_job = crud.create_job(
        db_session,
        schemas.JobCreate(
            title="Backend Engineer",
            company="Company",
            location="Remote",
            status="Applied",
        ),
    )
    session = crud.create_gmail_import_session(
        db_session,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )
    imported_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "imported-message",
            "thread_id": "thread-imported",
            "from": "recruiter@company.com",
            "subject": "Application received",
            "date": "2025-01-15T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Thank you for applying.",
                "body_text": "Thank you for applying for the Backend Engineer position.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
            "job_draft": {
                "title": "Backend Engineer",
                "company": "Company",
                "location": "Remote",
                "applied_date": "2025-01-15",
                "status": "Applied",
                "source": "Gmail",
            },
            "update_items": None,
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "needs_review": True,
        }
    )
    skipped_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "skipped-message",
            "thread_id": "thread-skipped",
            "from": "recruiter@company.com",
            "subject": "Application update",
            "date": "2025-01-16T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Update on your application.",
                "body_text": "Update on your application.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "APPLICATION_UPDATE", "confidence": 0.9, "reasons": ["update"]},
            "job_draft": None,
            "update_items": {
                "status": "Interview",
                "follow_up_date": "2025-01-16",
                "company": "Company",
                "title": "Backend Engineer",
            },
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "needs_review": True,
        }
    )
    deleted_job_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "deleted-job-message",
            "thread_id": "thread-deleted",
            "from": "recruiter@company.com",
            "subject": "Application received",
            "date": "2025-01-17T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Thank you for applying.",
                "body_text": "Thank you for applying for the Data Engineer position.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
            "job_draft": {
                "title": "Data Engineer",
                "company": "Company",
                "location": "Remote",
                "applied_date": "2025-01-17",
                "status": "Applied",
                "source": "Gmail",
            },
            "update_items": None,
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "needs_review": True,
        }
    )
    crud.update_gmail_import_session(
        db_session,
        session,
        status="completed",
        preview_payload=[imported_review, skipped_review, deleted_job_review],
        total_emails=3,
    )
    db_session.add_all(
        [
            models.GmailImportItem(
                session_id=session.id,
                gmail_message_id="imported-message",
                gmail_thread_id="thread-imported",
                from_email="recruiter@company.com",
                subject="Application received",
                payload_json=imported_review.model_dump_json(by_alias=True),
                selected_action="create",
                import_status="imported",
                linked_job_id=created_job.id,
            ),
            models.GmailImportItem(
                session_id=session.id,
                gmail_message_id="skipped-message",
                gmail_thread_id="thread-skipped",
                from_email="recruiter@company.com",
                subject="Application update",
                payload_json=skipped_review.model_dump_json(by_alias=True),
                selected_action="skip",
                import_status="skipped",
            ),
            models.GmailImportItem(
                session_id=session.id,
                gmail_message_id="deleted-job-message",
                gmail_thread_id="thread-deleted",
                from_email="recruiter@company.com",
                subject="Application received",
                payload_json=deleted_job_review.model_dump_json(by_alias=True),
                selected_action="create",
                import_status="imported",
                linked_job_id=999999,
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/gmail/import/preview/{session.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["jobs"][0]["gmail_message_id"] == "deleted-job-message"


def test_preview_gmail_import_only_fetches_missing_overlapping_range(client, db_session, monkeypatch) -> None:
    from backend.app.crud import crud
    from datetime import date

    cached_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "cached-message",
            "thread_id": "thread-cached",
            "from": "recruiter@company.com",
            "subject": "Application received",
            "date": "2025-04-15T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Thank you for applying.",
                "body_text": "Thank you for applying for the Backend Engineer position.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
            "job_draft": {
                "title": "Backend Engineer",
                "company": "Company",
                "location": "Remote",
                "applied_date": "2025-04-15",
                "status": "Applied",
                "source": "Gmail",
            },
            "update_items": None,
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "needs_review": True,
        }
    )
    new_review = GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": "new-message",
            "thread_id": "thread-new",
            "from": "recruiter@company.com",
            "subject": "Application received",
            "date": "2025-03-15T12:00:00Z",
            "source": "company_email",
            "email_content": {
                "snippet": "Thank you for applying.",
                "body_text": "Thank you for applying for the Data Engineer position.",
                "from_email": "recruiter@company.com",
                "from_domain": "company.com",
            },
            "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
            "job_draft": {
                "title": "Data Engineer",
                "company": "Company",
                "location": "Remote",
                "applied_date": "2025-03-15",
                "status": "Applied",
                "source": "Gmail",
            },
            "update_items": None,
            "extraction_candidates": {
                "title": [],
                "company": [],
                "location": [],
                "identifiers": {"gmail_thread_id": []},
            },
            "match_candidates": [],
            "best_match": None,
            "needs_review": True,
        }
    )
    cached_session = crud.create_gmail_import_session(
        db_session,
        start_date=date(2025, 4, 1),
        end_date=date(2025, 5, 1),
    )
    crud.update_gmail_import_session(
        db_session,
        cached_session,
        status="completed",
        total_emails=1,
        new_items=0,
        cached_items=1,
        cache_hit=True,
        preview_payload=[cached_review],
        error_message=None,
    )

    requested_queries: list[str] = []
    monkeypatch.setattr("backend.app.routers.gmail.get_gmail_service", lambda: object())
    monkeypatch.setattr(
        "backend.app.routers.gmail.list_message_ids_with_service",
        lambda service, q, max_results: requested_queries.append(q) or ["new-message"],
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.get_message_metadata_with_service",
        lambda service, message_id: {
            "id": message_id,
            "snippet": "Thank you for applying.",
            "payload": {
                "headers": [
                    {"name": "From", "value": "recruiter@company.com"},
                    {"name": "Subject", "value": "Application received"},
                ]
            },
        },
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.get_message_with_service",
        lambda service, message_id: {"id": message_id, "threadId": "thread-new"},
    )
    monkeypatch.setattr(
        "backend.app.routers.gmail.parse_gmail_message",
        lambda message, existing_jobs: new_review,
    )
    monkeypatch.setattr(
        gmail_router,
        "launch_gmail_preview_job",
        lambda session_id, start_date, end_date: gmail_router._run_gmail_preview_job(session_id, start_date, end_date),
    )
    monkeypatch.setattr(gmail_router, "_session_factory", lambda: TestingSessionLocal)

    start_response = client.post("/gmail/import/preview?start_date=2025-03-02&end_date=2025-05-01")

    assert start_response.status_code == 200
    preview_session_id = start_response.json()["session"]["id"]

    response = client.get(f"/gmail/import/preview/{preview_session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["status"] == "completed"
    assert payload["count"] == 2
    assert payload["session"]["cached_items"] == 1
    assert payload["session"]["new_items"] == 1
    assert len(requested_queries) == 1
    assert "after:2025/03/02" in requested_queries[0]
    assert "before:2025/04/01" in requested_queries[0]


def test_commit_gmail_import_creates_and_updates_jobs(client, db_session) -> None:
    from backend.app.crud import crud
    from backend.app.models import models
    from backend.app.schemas import schemas
    from datetime import date

    existing_job = crud.create_job(
        db_session,
        schemas.JobCreate(
            title="Backend Engineer",
            company="Company",
            location="Remote",
            status="Applied",
        ),
    )
    session = crud.create_gmail_import_session(db_session, start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
    crud.update_gmail_import_session(
        db_session,
        session,
        preview_payload=[
            GmailParsedMessageReview.model_validate(
                {
                    "gmail_message_id": "create-message",
                    "thread_id": "thread-1",
                    "from": "recruiter@company.com",
                    "subject": "Application received",
                    "date": "2025-01-15T12:00:00Z",
                    "source": "company_email",
                    "email_content": {
                        "snippet": "Thank you for applying.",
                        "body_text": "Thank you for applying for the Data Engineer position.",
                        "from_email": "recruiter@company.com",
                        "from_domain": "company.com",
                    },
                    "classification": {"label": "NEW_APPLICATION", "confidence": 0.9, "reasons": ["confirmation"]},
                    "job_draft": {
                        "title": "Data Engineer",
                        "company": "Company",
                        "location": "Remote",
                        "applied_date": "2025-01-15",
                        "status": "Applied",
                        "source": "Gmail",
                    },
                    "update_items": None,
                    "extraction_candidates": {
                        "title": [],
                        "company": [],
                        "location": [],
                        "identifiers": {"gmail_thread_id": []},
                    },
                    "match_candidates": [],
                    "best_match": None,
                    "needs_review": True,
                }
            ),
            GmailParsedMessageReview.model_validate(
                {
                    "gmail_message_id": "update-message",
                    "thread_id": "thread-2",
                    "from": "recruiter@company.com",
                    "subject": "Interview scheduled",
                    "date": "2025-01-16T12:00:00Z",
                    "source": "company_email",
                    "email_content": {
                        "snippet": "Interview scheduled.",
                        "body_text": "Your interview has been scheduled.",
                        "from_email": "recruiter@company.com",
                        "from_domain": "company.com",
                    },
                    "classification": {"label": "INTERVIEW", "confidence": 0.9, "reasons": ["interview"]},
                    "job_draft": None,
                    "update_items": {
                        "status": "Interview",
                        "follow_up_date": "2025-01-16",
                        "company": "Company",
                        "title": "Backend Engineer",
                    },
                    "extraction_candidates": {
                        "title": [],
                        "company": [],
                        "location": [],
                        "identifiers": {"gmail_thread_id": []},
                    },
                    "match_candidates": [],
                    "best_match": None,
                    "needs_review": True,
                }
            ),
        ],
    )
    db_session.add_all(
        [
            models.GmailImportItem(
                session_id=session.id,
                gmail_message_id="create-message",
                gmail_thread_id="thread-1",
                from_email="recruiter@company.com",
                subject="Application received",
                payload_json="{}",
                selected_action="create",
                import_status="pending",
            ),
            models.GmailImportItem(
                session_id=session.id,
                gmail_message_id="update-message",
                gmail_thread_id="thread-2",
                from_email="recruiter@company.com",
                subject="Interview scheduled",
                payload_json="{}",
                selected_action="update",
                import_status="pending",
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/gmail/import/commit",
        json={
            "session_id": session.id,
            "items": [
                {
                    "gmail_message_id": "create-message",
                    "action": "create",
                    "job_draft": {
                        "title": "Data Engineer",
                        "company": "Company",
                        "location": "Remote",
                        "applied_date": "2025-01-15",
                        "status": "Applied",
                        "source": "Gmail",
                    },
                },
                {
                    "gmail_message_id": "update-message",
                    "action": "update",
                    "target_job_id": existing_job.id,
                    "update_items": {
                        "status": "Interview",
                        "follow_up_date": "2025-01-16",
                        "notes": "Imported from Gmail update.",
                    },
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["status"] == "completed"
    assert len(payload["results"]) == 2
    assert any(result["action"] == "create" and result["status"] == "imported" for result in payload["results"])
    assert any(result["action"] == "update" and result["status"] == "imported" for result in payload["results"])


def test_get_jobs_from_gmail_handles_service_errors(client, monkeypatch) -> None:
    monkeypatch.setattr("backend.app.routers.gmail.crud.get_jobs", lambda db, skip, limit: [])
    monkeypatch.setattr(
        "backend.app.routers.gmail.fetch_job_applications_from_gmail",
        lambda query, max_results, existing_jobs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    response = client.get("/gmail/jobs")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch Gmail jobs: boom"
