import json
from pathlib import Path
from typing import Optional

import pytest

from backend.app.schemas.schemas import GmailClassificationResult, GmailParsedMessageReview
from backend.app.services import gmail_client


class FakeCredentials:
    def __init__(
        self,
        *,
        valid: bool = True,
        expired: bool = False,
        refresh_token: Optional[str] = "refresh-token",
        token: str = "token",
    ) -> None:
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.token = token
        self.refreshed = False

    def refresh(self, _request: object) -> None:
        self.valid = True
        self.expired = False
        self.refreshed = True
        self.token = "refreshed-token"

    def to_json(self) -> str:
        return json.dumps(
            {
                "token": self.token,
                "refresh_token": self.refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "scopes": gmail_client.SCOPES,
            }
        )


def test_load_credentials_returns_none_when_token_file_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gmail_client, "TOKEN_PATH", tmp_path / "missing.json")

    assert gmail_client.load_credentials() is None


def test_resolve_redirect_uri_prefers_configured_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gmail_client,
        "get_configured_redirect_uris",
        lambda: [
            "http://localhost:8000/external/auth/callback",
            "http://127.0.0.1:8000/gmail/auth/callback",
        ],
    )

    assert (
        gmail_client.resolve_redirect_uri("http://localhost:8000/external/auth/callback")
        == "http://localhost:8000/external/auth/callback"
    )


def test_resolve_redirect_uri_falls_back_to_first_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gmail_client,
        "get_configured_redirect_uris",
        lambda: ["http://localhost:8000/external/auth/callback"],
    )

    assert (
        gmail_client.resolve_redirect_uri("http://127.0.0.1:8000/gmail/auth/callback")
        == "http://localhost:8000/external/auth/callback"
    )


def test_refresh_credentials_if_needed_refreshes_and_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    token_path = tmp_path / "gmail_token.json"
    monkeypatch.setattr(gmail_client, "TOKEN_PATH", token_path)
    monkeypatch.setattr(gmail_client, "_request_class", lambda: (lambda: object()))

    creds = FakeCredentials(valid=False, expired=True)

    refreshed = gmail_client.refresh_credentials_if_needed(creds)

    assert refreshed is creds
    assert creds.refreshed is True
    assert json.loads(token_path.read_text())["token"] == "refreshed-token"


def test_refresh_credentials_if_needed_raises_without_refresh_token() -> None:
    creds = FakeCredentials(valid=False, expired=True, refresh_token=None)

    with pytest.raises(RuntimeError, match="cannot be refreshed"):
        gmail_client.refresh_credentials_if_needed(creds)


def test_get_valid_credentials_refreshes_loaded_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    creds = FakeCredentials(valid=False, expired=True)
    monkeypatch.setattr(gmail_client, "load_credentials", lambda: creds)
    monkeypatch.setattr(gmail_client, "refresh_credentials_if_needed", lambda value: value)

    assert gmail_client.get_valid_credentials() is creds


def test_get_valid_credentials_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gmail_client, "load_credentials", lambda: None)

    with pytest.raises(RuntimeError, match="No credentials"):
        gmail_client.get_valid_credentials()


def test_list_message_ids_uses_gmail_service(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMessagesApi:
        def list(self, **kwargs: object) -> "FakeMessagesApi":
            assert kwargs == {"userId": "me", "q": "label:inbox", "maxResults": 5}
            return self

        def execute(self) -> dict[str, object]:
            return {"messages": [{"id": "1"}, {"id": "2"}]}

    class FakeUsersApi:
        def messages(self) -> FakeMessagesApi:
            return FakeMessagesApi()

    class FakeService:
        def users(self) -> FakeUsersApi:
            return FakeUsersApi()

    monkeypatch.setattr(gmail_client, "get_valid_credentials", lambda: FakeCredentials())
    monkeypatch.setattr(gmail_client, "_build_gmail_service", lambda creds: FakeService())

    assert gmail_client.list_message_ids(q="label:inbox", max_results=5) == ["1", "2"]


def test_get_message_uses_expected_gmail_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    message = {"id": "abc"}

    class FakeMessagesApi:
        def get(self, **kwargs: object) -> "FakeMessagesApi":
            assert kwargs == {"userId": "me", "id": "abc", "format": "full"}
            return self

        def execute(self) -> dict[str, str]:
            return message

    class FakeUsersApi:
        def messages(self) -> FakeMessagesApi:
            return FakeMessagesApi()

    class FakeService:
        def users(self) -> FakeUsersApi:
            return FakeUsersApi()

    monkeypatch.setattr(gmail_client, "get_valid_credentials", lambda: FakeCredentials())
    monkeypatch.setattr(gmail_client, "_build_gmail_service", lambda creds: FakeService())

    assert gmail_client.get_message("abc") == message


def test_fetch_job_applications_from_gmail_filters_irrelevant(monkeypatch: pytest.MonkeyPatch) -> None:
    message_ids = ["keep", "skip"]
    kept_message = {"id": "keep", "threadId": "thread-1"}
    skipped_message = {"id": "skip", "threadId": "thread-2"}

    monkeypatch.setattr(gmail_client, "list_message_ids", lambda q, max_results: message_ids)
    monkeypatch.setattr(
        gmail_client,
        "get_message",
        lambda msg_id: kept_message if msg_id == "keep" else skipped_message,
    )

    def fake_parse(message: dict[str, object], existing_jobs: list[object]) -> GmailParsedMessageReview:
        label = "NEW_APPLICATION" if message["id"] == "keep" else "IRRELEVANT"
        return GmailParsedMessageReview.model_validate(
            {
                "gmail_message_id": message["id"],
                "thread_id": message["threadId"],
                "from": "jobs@example.com",
                "subject": "Subject",
                "date": None,
                "source": "company_email",
                "email_content": {
                    "snippet": "snippet",
                    "body_text": "body",
                    "from_email": "jobs@example.com",
                    "from_domain": "example.com",
                },
                "classification": GmailClassificationResult(
                    label=label,
                    confidence=0.9,
                    reasons=["test_reason"],
                ),
                "job_draft": None,
                "update_items": None,
                "extraction_candidates": {
                    "title": [],
                    "company": [],
                    "location": [],
                    "identifiers": {
                        "gmail_thread_id": [],
                    },
                },
                "match_candidates": [],
                "best_match": None,
                "needs_review": True,
            }
        )

    monkeypatch.setattr(gmail_client, "parse_gmail_message", fake_parse)

    results = gmail_client.fetch_job_applications_from_gmail("query", 5, existing_jobs=[])

    assert [result.gmail_message_id for result in results] == ["keep"]
