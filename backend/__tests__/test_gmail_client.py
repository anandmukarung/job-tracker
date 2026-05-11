import base64
import json
from pathlib import Path
from typing import Optional

import pytest

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


def test_is_job_application_email_matches_confirmation_and_update_phrases() -> None:
    body = base64.urlsafe_b64encode(b"Thank you for applying").decode("utf-8")
    confirmation_msg = {
        "payload": {
            "headers": [
                {"name": "From", "value": "hiring@company.com"},
                {"name": "Subject", "value": "Application received"},
            ],
            "body": {"data": body},
        },
        "snippet": "",
    }
    update_msg = {
        "payload": {
            "headers": [
                {"name": "From", "value": "recruiter@company.com"},
                {"name": "Subject", "value": "Interview update"},
            ],
            "body": {"data": ""},
        },
        "snippet": "",
    }

    assert gmail_client.is_job_application_email(confirmation_msg) is True
    assert gmail_client.is_job_application_email(update_msg) is True


def test_is_job_application_email_excludes_third_party_platforms() -> None:
    msg = {
        "payload": {
            "headers": [
                {"name": "From", "value": "jobs-noreply@linkedin.com"},
                {"name": "Subject", "value": "Thank you for applying"},
            ],
            "body": {"data": ""},
        },
        "snippet": "",
    }

    assert gmail_client.is_job_application_email(msg) is False


def test_fetch_job_applications_from_gmail_filters_non_job_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = {
        "1": {"payload": {"headers": []}, "snippet": ""},
        "2": {"payload": {"headers": []}, "snippet": ""},
    }
    monkeypatch.setattr(gmail_client, "list_message_ids", lambda q, max_results: ["1", "2"])
    monkeypatch.setattr(gmail_client, "get_message", lambda msg_id: messages[msg_id])
    monkeypatch.setattr(gmail_client, "is_job_application_email", lambda msg: msg is messages["1"])
    monkeypatch.setattr(
        gmail_client,
        "parse_job_candidates_from_message",
        lambda msg: [{"subject": "Matched", "from": "recruiter@company.com"}],
    )

    jobs = gmail_client.fetch_job_applications_from_gmail("applied", 10)

    assert jobs == [{"subject": "Matched", "from": "recruiter@company.com"}]
