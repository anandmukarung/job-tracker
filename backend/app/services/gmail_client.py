import json
import base64
from typing import TYPE_CHECKING, Any, Optional, cast
from pathlib import Path

if TYPE_CHECKING:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials as GoogleCredentials
    from google_auth_oauthlib.flow import Flow as GoogleFlow
else:
    GoogleCredentials = Any
    GoogleFlow = Any
    GoogleRequest = Any

try:
    from google.oauth2.credentials import Credentials as RuntimeCredentials
    from google.auth.transport.requests import Request as RuntimeRequest
    from google_auth_oauthlib.flow import Flow as RuntimeFlow
    from googleapiclient.discovery import build as google_build
except ModuleNotFoundError:  # pragma: no cover - handled at runtime when Gmail features are used
    RuntimeCredentials = None
    RuntimeRequest = None
    RuntimeFlow = None
    google_build = None

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = BASE_DIR / "credentials" / "credentials.json"
TOKEN_PATH = BASE_DIR / "token" / "gmail_token.json"

# Scopes we need
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Possible messages for application confirmation
CONFIRMATION_PHRASES = [
    "thank you for applying",
    "your application has been received",
    "application received",
    "we have received your application",
    "you applied for",
    "application submitted",
]

# Possible messages for application updates
UPDATE_PHRASES = [
    "update on your application",
    "status of your application",
    "we have reviewed your application",
    "your application status has changed",
    "we regret to inform you",
    "we’re excited to move forward",
    "interview",
    "offer",
    "unfortunately"
]

# Separate 3rd party communications
def is_third_party_platform(from_email: str) -> bool:
    return any(domain in from_email.lower() for domain in ["linkedin", "indeed", "glassdoor"])

# Helper: create OAuth flow (used to generate consent URL)
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
        redirect_uri=redirect_uri
    )

# Get consent URL for user to visit
def get_authorize_url(redirect_uri: str) -> str:
    flow = make_auth_flow(redirect_uri)
    auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    return auth_url

# Exchange code for tokens and save them
def exchange_code_and_save_tokens(code: str, redirect_uri: str) -> dict[str, Any]:
    flow = make_auth_flow(redirect_uri)
    flow.fetch_token(code=code)
    creds = cast(GoogleCredentials, flow.credentials)
    _save_credentials(creds)
    return json.loads(creds.to_json())


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


# Load stored credentials
def load_credentials() -> Optional[GoogleCredentials]:
    if not TOKEN_PATH.exists():
        return None
    data = json.loads(TOKEN_PATH.read_text())
    creds = _credentials_class().from_authorized_user_info(data, SCOPES)
    return creds

# Fetch messages list using Gmail API with a query (q param is Gmail search query)
def list_message_ids(q: str = "", max_results: int = 50) -> list[str]:
    creds = get_valid_credentials()
    service = _build_gmail_service(creds)
    res = service.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    messages = res.get("messages", [])
    return [m["id"] for m in messages]

# Fetch full message by id and return parsed bodies/snippet/headers
def get_message(msg_id: str) -> dict[str, Any]:
    creds = get_valid_credentials()
    service = _build_gmail_service(creds)
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    return msg

# Helper: extract readable text/html body from message payload
def _get_message_body_parts(payload: dict[str, Any]) -> str:
    if payload.get("parts"):
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            if mime == "text/html":
                raw = part["body"].get("data")
                if raw:
                    return base64.urlsafe_b64decode(raw).decode("utf-8", errors="ignore")
            if part.get("parts"):
                # nested parts
                result = _get_message_body_parts(part)
                if result:
                    return result
    else:
        # no parts - check payload body
        raw = payload.get("body", {}).get("data")
        if raw:
            return base64.urlsafe_b64decode(raw).decode("utf-8", errors="ignore")
    return ""

# Parse a message to extract possible job entries
def parse_job_candidates_from_message(msg: dict[str, Any]) -> list[dict[str, str]]:
    # Subject & snippet
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    from_email = headers.get("from", "")
    subject = headers.get("subject", "")
    
    result = [{"from": from_email, "subject": subject }]
    return result

def is_job_application_email(msg: dict[str, Any]) -> bool:
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    from_email = headers.get("from", "")
    subject = headers.get("subject", "")
    snippet = msg.get("snippet", "")
    body = _get_message_body_parts(payload) or snippet

    if (is_third_party_platform(from_email)):
        return False
    
    content = f"{subject} {body}".lower()
    if any(p in content for p in CONFIRMATION_PHRASES):
        return True
    if any(p in content for p in UPDATE_PHRASES):
        return True
    
    return False


# High-level: fetch email-job candidates via query and return parsed list
def fetch_job_applications_from_gmail(query: str, max_results: int) -> list[dict[str, str]]:
    ids = list_message_ids(q=query, max_results=max_results)
    candidates: list[dict[str, str]] = []
    for msg_id in ids:
        msg = get_message(msg_id)
        if is_job_application_email(msg):
            candidates.extend(parse_job_candidates_from_message(msg))
    return candidates
