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

# Parse a message to extract possible job entries (very heuristic)
def parse_job_candidates_from_message(msg: Dict) -> List[Dict]:
    # Subject & snippet
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    date = headers.get("date", "")
    snippet = msg.get("snippet", "")
    body_html = _get_message_body_parts(msg.get("payload", {})) or snippet or ""

    candidates = []
    # heuristics / regex examples - tweak to your observed email formats
    # Example LinkedIn: "You applied to Software Engineer at OpenAI"
    m = re.search(r"You applied to\s+(.+?)\s+at\s+([^\n<.,]+)", body_html, re.I)
    if m:
        candidates.append({
            "title": m.group(1).strip(),
            "company": m.group(2).strip(),
            "source": "LinkedIn",
            "applied_date": date,
            "job_link": None
        })

    # Other generic patterns
    m2 = re.search(r"application (?:received|submitted) for (.+?) at (.+?)", body_html, re.I)
    if m2:
        candidates.append({
            "title": m2.group(1).strip(),
            "company": m2.group(2).strip(),
            "source": "unknown",
            "applied_date": date,
            "job_link": None
        })

    # extract anchors pointing to common job sources
    for anchor_match in re.finditer(r'href=[\'"]([^\'"]+)[\'"].*?>([^<]+)</a>', body_html, re.I|re.S):
        href, text = anchor_match.groups()
        if "linkedin.com" in href or "indeed.com" in href or "jobs." in href:
            candidates.append({
                "title": text.strip() or subject,
                "company": headers.get("from", "").split("@")[0],
                "source": "link",
                "applied_date": date,
                "job_link": href
            })

    # fallback: use subject if it contains applied wording
    if not candidates and re.search(r"(applied|application received|application submitted)", subject, re.I):
        # try to extract "title at company" from subject
        m3 = re.search(r"(.+?) at (.+)", subject)
        if m3:
            candidates.append({
                "title": m3.group(1).strip(),
                "company": m3.group(2).strip(),
                "source": "email-subject",
                "applied_date": date,
                "job_link": None
            })

    # dedupe by title+company
    seen = set()
    uniq = []
    for c in candidates:
        key = (c.get("title","").lower(), c.get("company","").lower())
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq

# High-level: fetch email-job candidates via query and return parsed list
def fetch_job_candidates_from_gmail(query: str = "applied OR \"thank you for your application\" newer_than:365d", max_results: int = 50) -> List[Dict]:
    ids = list_message_ids(q=query, max_results=max_results)
    candidates = []
    for id_ in ids:
        msg = get_message(id_)
        candidates.extend(parse_job_candidates_from_message(msg))
    return candidates