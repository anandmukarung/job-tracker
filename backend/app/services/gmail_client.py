import os
import json
import base64
import re
from typing import List, Dict, Optional
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
def make_auth_flow(redirect_uri: str) -> Flow:
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError("Put your credentials.json at backend/credentials/credentials.json")
    return Flow.from_client_secrets_file(
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
def exchange_code_and_save_tokens(code: str, redirect_uri: str) -> Dict:
    flow = make_auth_flow(redirect_uri)
    flow.fetch_token(code=code)
    creds = flow.credentials
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    return json.loads(creds.to_json())

# Load stored credentials
def load_credentials() -> Optional[Credentials]:
    if not TOKEN_PATH.exists():
        return None
    data = json.loads(TOKEN_PATH.read_text())
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    return creds

# Fetch messages list using Gmail API with a query (q param is Gmail search query)
def list_message_ids(q: str = "", max_results: int = 50) -> List[str]:
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("No credentials. Authorize first.")
    try:
        service = build('gmail', 'v1', credentials=creds)
        res = service.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
        messages = res.get("messages", [])
        return [m["id"] for m in messages]
    except HttpError as e:
        raise

# Fetch full message by id and return parsed bodies/snippet/headers
def get_message(msg_id: str) -> Dict:
    creds = load_credentials()
    service = build('gmail', 'v1', credentials=creds)
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    return msg

# Helper: extract readable text/html body from message payload
def _get_message_body_parts(payload):
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
def parse_job_candidates_from_message(msg: Dict) -> List[Dict]:
    # Subject & snippet
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    from_email = headers.get("from", "")
    subject = headers.get("subject", "")
    
    result = [{"from": from_email, "subject": subject }]
    return result

def is_job_application_email(msg: Dict) -> bool:
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
    
    return False


# High-level: fetch email-job candidates via query and return parsed list
def fetch_job_applications_from_gmail(query: str , max_results: int) -> List[Dict]:
    ids = list_message_ids(q=query, max_results=max_results)
    candidates = []
    for id_ in ids:
        msg = get_message(id_)
        if(is_job_application_email(msg)):
            candidates.extend(parse_job_candidates_from_message(msg))
    return candidates