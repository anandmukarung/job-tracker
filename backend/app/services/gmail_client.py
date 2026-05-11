import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, cast

from ..schemas.schemas import GmailParsedMessageReview
from .email_parser import parse_gmail_message

if TYPE_CHECKING:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials as GoogleCredentials
    from google_auth_oauthlib.flow import Flow as GoogleFlow
else:
    GoogleCredentials = Any
    GoogleFlow = Any
    GoogleRequest = Any

try:
    from google.auth.transport.requests import Request as RuntimeRequest
    from google.oauth2.credentials import Credentials as RuntimeCredentials
    from google_auth_oauthlib.flow import Flow as RuntimeFlow
    from googleapiclient.discovery import build as google_build
except ModuleNotFoundError:  # pragma: no cover - handled at runtime when Gmail features are used
    RuntimeCredentials = None
    RuntimeFlow = None
    RuntimeRequest = None
    google_build = None


BASE_DIR = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = BASE_DIR / "credentials" / "credentials.json"
TOKEN_PATH = BASE_DIR / "token" / "gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _require_google_client() -> None:
    if google_build is None:
        raise RuntimeError(
            "Google API dependencies are not installed. Install requirements.txt to use Gmail features."
        )


def _credentials_class() -> type[GoogleCredentials]:
    _require_google_client()
    assert RuntimeCredentials is not None
    return RuntimeCredentials


def _request_class() -> type[GoogleRequest]:
    _require_google_client()
    assert RuntimeRequest is not None
    return RuntimeRequest


def _flow_class() -> type[GoogleFlow]:
    _require_google_client()
    assert RuntimeFlow is not None
    return RuntimeFlow


def _build_gmail_service(creds: GoogleCredentials) -> Any:
    _require_google_client()
    assert google_build is not None
    return google_build("gmail", "v1", credentials=creds)


def _load_client_config() -> dict[str, Any]:
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError("Put your credentials.json at backend/credentials/credentials.json")
    return json.loads(CREDENTIALS_PATH.read_text())


def get_configured_redirect_uris() -> list[str]:
    config = _load_client_config()
    oauth_config = config.get("web") or config.get("installed") or {}
    redirect_uris = oauth_config.get("redirect_uris", [])
    return [uri for uri in redirect_uris if isinstance(uri, str)]


def resolve_redirect_uri(preferred_redirect_uri: str) -> str:
    redirect_uris = get_configured_redirect_uris()
    if not redirect_uris:
        return preferred_redirect_uri
    if preferred_redirect_uri in redirect_uris:
        return preferred_redirect_uri
    return redirect_uris[0]


def _save_credentials(creds: GoogleCredentials) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())


def make_auth_flow(redirect_uri: str) -> GoogleFlow:
    _require_google_client()
    redirect_uri = resolve_redirect_uri(redirect_uri)
    return _flow_class().from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


def get_authorize_url(redirect_uri: str) -> str:
    flow = make_auth_flow(redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code_and_save_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    flow = make_auth_flow(redirect_uri)
    flow.fetch_token(code=code)
    creds = cast(GoogleCredentials, flow.credentials)
    _save_credentials(creds)
    return json.loads(creds.to_json())


def load_credentials() -> Optional[GoogleCredentials]:
    if not TOKEN_PATH.exists():
        return None
    data = json.loads(TOKEN_PATH.read_text())
    return _credentials_class().from_authorized_user_info(data, SCOPES)


def refresh_credentials_if_needed(creds: GoogleCredentials) -> GoogleCredentials:
    if not getattr(creds, "expired", False):
        return creds
    if not getattr(creds, "refresh_token", None):
        raise RuntimeError("Stored Gmail credentials are expired and cannot be refreshed.")
    creds.refresh(_request_class()())
    _save_credentials(creds)
    return creds


def get_valid_credentials() -> GoogleCredentials:
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("No credentials. Authorize first.")
    return refresh_credentials_if_needed(creds)


def list_message_ids(q: str = "", max_results: int = 50) -> list[str]:
    creds = get_valid_credentials()
    service = _build_gmail_service(creds)
    response = service.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    messages = response.get("messages", [])
    return [message["id"] for message in messages]


def get_message(msg_id: str) -> dict[str, Any]:
    creds = get_valid_credentials()
    service = _build_gmail_service(creds)
    return service.users().messages().get(userId="me", id=msg_id, format="full").execute()


def fetch_job_applications_from_gmail(
    query: str,
    max_results: int,
    existing_jobs: Optional[list[Any]] = None,
) -> list[GmailParsedMessageReview]:
    print(f"[gmail] fetch start query={query!r} max_results={max_results}")
    message_ids = list_message_ids(q=query, max_results=max_results)
    print(f"[gmail] fetched message ids count={len(message_ids)}")

    jobs: list[GmailParsedMessageReview] = []
    for message_id in message_ids:
        print(f"[gmail] fetching message id={message_id}")
        message = get_message(message_id)
        parsed = parse_gmail_message(message, existing_jobs=existing_jobs or [])
        print(
            "[gmail] parsed",
            {
                "message_id": parsed.gmail_message_id,
                "classification": parsed.classification.label,
                "source": parsed.source,
                "title": parsed.job_draft.title if parsed.job_draft else parsed.update_items.title if parsed.update_items else None,
                "company": parsed.job_draft.company if parsed.job_draft else parsed.update_items.company if parsed.update_items else None,
                "best_match": parsed.best_match.job_id if parsed.best_match else None,
            },
        )
        if parsed.classification.label == "IRRELEVANT":
            print(f"[gmail] skipped message id={message_id} reason=irrelevant")
            continue
        jobs.append(parsed)

    print(f"[gmail] final extracted listings count={len(jobs)}")
    return jobs
