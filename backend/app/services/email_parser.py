import base64
import html
import re
from datetime import date, datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from ..schemas.schemas import (
    GmailCandidate,
    GmailClassificationResult,
    GmailEmailContent,
    GmailExtractionCandidates,
    GmailIdentifierCandidates,
    GmailJobDraft,
    GmailMatchCandidate,
    GmailMessageClassification,
    GmailParsedMessageReview,
    GmailSource,
    GmailUpdateItems,
)


TITLE_KEYWORDS = (
    "engineer",
    "developer",
    "analyst",
    "manager",
    "intern",
    "associate",
    "specialist",
    "scientist",
    "designer",
    "consultant",
    "administrator",
    "architect",
)
GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "aol.com",
    "example.com",
}
THIRD_PARTY_PLATFORM_DOMAINS = ("linkedin", "indeed", "glassdoor")
PROMO_TERMS = (
    "credit",
    "pre-approved",
    "preapproved",
    "special offer",
    "limited time",
    "apr",
    "rate",
    "goodleap",
    "promotion",
    "marketing",
    "exclusive offer",
    "loan",
    "financing",
    "unsubscribe",
)
JOB_CONTEXT_TERMS = (
    "application",
    "applied",
    "role",
    "position",
    "candidate",
    "recruiting",
    "talent",
    "job",
)
NEW_APPLICATION_PHRASES = (
    "thank you for applying",
    "your application has been received",
    "application received",
    "we have received your application",
    "application submitted",
    "thank you for applying for",
)
APPLICATION_UPDATE_PHRASES = (
    "update on your application",
    "application update",
    "status of your application",
    "your application status",
    "regarding your application",
)
BROADER_UPDATE_PHRASES = (
    "following up on your application",
    "follow up on your application",
    "follow-up on your application",
    "next steps",
    "next step",
    "application progress",
    "moving forward with your application",
    "moving ahead with your application",
    "decision on your application",
    "reviewed your application",
)
INTERVIEW_PHRASES = (
    "schedule an interview",
    "interview has been scheduled",
    "interview scheduled",
    "schedule your interview",
    "invitation to interview",
    "phone screen",
    "technical screen",
    "interview invitation",
)
REJECTION_PHRASES = (
    "we regret to inform you",
    "will not be moving forward",
    "not selected",
    "decided to move forward with other candidates",
    "after careful consideration",
    "carefully considered",
    "thoroughly reviewed",
    "after careful review",
)
OFFER_PHRASES = (
    "offer of employment",
    "employment offer",
    "job offer",
    "offer letter",
    "we are pleased to offer you",
    "formal offer",
)
JOB_ALERT_PHRASES = (
    "job alert",
    "new jobs for you",
    "recommended jobs",
    "similar jobs",
)
REMOTE_LOCATION_PHRASES = (
    "remote",
    "work from home",
    "fully remote",
    "100% remote",
)
GENERIC_LOCAL_PARTS = {"noreply", "no-reply", "support", "team", "careers", "recruiting", "jobs"}


def _get_message_headers(msg: dict[str, Any]) -> dict[str, str]:
    return {
        header["name"].lower(): header["value"]
        for header in msg.get("payload", {}).get("headers", [])
        if "name" in header and "value" in header
    }


def _extract_email_address(from_header: str) -> str:
    match = re.search(r"<([^>]+)>", from_header)
    return (match.group(1) if match else from_header).strip().lower()


def _extract_display_name(from_header: str) -> str:
    match = re.match(r"\s*\"?([^\"<]+?)\"?\s*<[^>]+>", from_header)
    if match:
        return match.group(1).strip()
    if "@" in from_header:
        return ""
    return from_header.strip()


def _decode_payload_data(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _clean_body_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"https?://[^\s\"'>)]+", " ", text)
    text = re.sub(r"\bwww\.[^\s\"'>)]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _extract_raw_message_body(payload: dict[str, Any]) -> str:
    parts = payload.get("parts", [])
    if parts:
        fragments: list[str] = []
        for part in parts:
            mime_type = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if mime_type in {"text/plain", "text/html"} and data:
                fragments.append(_decode_payload_data(data))
            if part.get("parts"):
                nested = _extract_raw_message_body(part)
                if nested:
                    fragments.append(nested)
        return "\n".join(fragment for fragment in fragments if fragment).strip()

    data = payload.get("body", {}).get("data")
    return _decode_payload_data(data) if data else ""


def _extract_message_body(payload: dict[str, Any]) -> str:
    return _clean_body_text(_extract_raw_message_body(payload))


def _extract_links(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"'>)]+", text)
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        cleaned = re.sub(r"</[^>]+$", "", url.rstrip(".,)"))
        cleaned = re.sub(r"[<>\"]+$", "", cleaned)
        if cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered


def _first_sentence(text: str) -> str:
    parts = re.split(r"[.!?\n]", text, maxsplit=1)
    return parts[0].strip() if parts else text.strip()


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_candidate_value(value: str) -> str:
    value = _normalize_whitespace(value.strip(" :-|,"))
    if value.lower().startswith("the "):
        value = value[4:].strip()
    return value


def _normalize_comparison(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _add_candidate(
    candidates: list[GmailCandidate],
    value: Optional[str],
    confidence: float,
    source: str,
) -> None:
    if not value:
        return
    cleaned = _clean_candidate_value(value)
    if len(cleaned) < 2:
        return
    existing = next((candidate for candidate in candidates if candidate.value.lower() == cleaned.lower()), None)
    if existing is None:
        candidates.append(GmailCandidate(value=cleaned, confidence=confidence, source=source))
        return
    if sum(1 for char in cleaned if char.isupper()) > sum(1 for char in existing.value if char.isupper()):
        existing.value = cleaned
    if confidence > existing.confidence:
        existing.confidence = confidence
        existing.source = source


def _domain_from_email(email_address: str) -> str:
    if "@" not in email_address:
        return ""
    return email_address.split("@", 1)[1].lower()


def _looks_corporate_name(name: str) -> bool:
    if not name:
        return False
    lowered = name.lower()
    return lowered not in GENERIC_LOCAL_PARTS and not any(lowered.startswith(prefix + " ") for prefix in GENERIC_LOCAL_PARTS)


def _company_from_sender(from_header: str) -> Optional[str]:
    display_name = _extract_display_name(from_header)
    if display_name and _looks_corporate_name(display_name):
        cleaned = re.sub(r"\b(careers|recruiting|talent acquisition|jobs)\b", "", display_name, flags=re.IGNORECASE)
        cleaned = _normalize_whitespace(cleaned).strip(" -")
        if cleaned:
            return cleaned

    email_address = _extract_email_address(from_header)
    domain = _domain_from_email(email_address)
    if not domain or domain in GENERIC_EMAIL_DOMAINS or any(part in domain for part in THIRD_PARTY_PLATFORM_DOMAINS):
        return None

    local_part = email_address.split("@", 1)[0]
    if domain.endswith(".myworkday.com"):
        company_label = domain[: -len(".myworkday.com")].split(".")[-1]
        company = company_label.replace("-", " ").replace("_", " ").strip()
        return company.title() if company else None
    if domain == "myworkday.com" and local_part not in GENERIC_LOCAL_PARTS:
        company = local_part.replace("-", " ").replace("_", " ").strip()
        return company.title() if company else None

    label = domain.split(".")[0]
    if label in {"mail", "email", "jobs", "careers", "recruiting"}:
        parts = domain.split(".")
        if len(parts) > 1:
            label = parts[1]
    company = label.replace("-", " ").replace("_", " ").strip()
    return company.title() if company else None


def _company_from_text(text: str) -> Optional[str]:
    patterns = (
        r"thank you for your interest in (?P<company>.+?)(?:[.!:\n]|$)",
        r"thank you for applying to (?P<company>.+?)(?:[.!:\n]|$)",
        r"(?:position|role)\s+at (?P<company>[A-Z][A-Za-z0-9& .'\-]{1,60}?)(?:[.!:\n]|$)",
        r"\bto (?P<company>[A-Z][A-Za-z0-9& .'\-]{1,60}?)(?:\s+for|\s+regarding|\s+about|\s+on|[.!:\n]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        company = re.sub(
            r"\b(for|the|position|role|job|opportunity)\b.*$",
            "",
            match.group("company"),
            flags=re.IGNORECASE,
        )
        company = _clean_candidate_value(company)
        if company:
            return company
    return None


def _extract_title_texts(text: str) -> list[tuple[str, str, float]]:
    patterns = (
        (
            r"job\s*#\s*(?P<job_id>[A-Za-z0-9\-]{3,})\s*[-:|]\s*(?P<title>.+?)(?:\s+position|\s+role| at | has been|[.!:\n]|$)",
            "subject_job_number",
            0.95,
        ),
        (
            r"(?P<job_id>[A-Za-z0-9\-]{3,})\s*[-:|]\s*(?P<title>.+?)(?:\s+position|\s+role| at | has been|[.!:\n]|$)",
            "leading_job_number",
            0.88,
        ),
        (
            r"thank you for applying for(?: the)? (?P<title>.+?)(?:\s+position|\s+role| at |[.!:\n]|$)",
            "application_phrase",
            0.9,
        ),
        (
            r"your application for (?P<title>.+?)(?:\s+position|\s+role| at |[.!:\n]|$)",
            "application_subject",
            0.9,
        ),
        (
            r"interview for (?P<title>.+?)(?:\s+position|\s+role| at |[.!:\n]|$)",
            "interview_phrase",
            0.86,
        ),
        (
            r"for the (?P<title>.+?)(?:\s+position|\s+role| at |[.!:\n]|$)",
            "generic_position_phrase",
            0.78,
        ),
    )
    matches: list[tuple[str, str, float]] = []
    for pattern, source, confidence in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        title = _clean_candidate_value(match.group("title"))
        if any(keyword in title.lower() for keyword in TITLE_KEYWORDS):
            matches.append((title, source, confidence))
        elif len(title.split()) <= 8:
            matches.append((title, source, confidence - 0.08))
    return matches


def _extract_title_keyword_phrase(text: str) -> Optional[str]:
    lines = [_normalize_whitespace(line) for line in text.splitlines() if line.strip()]
    for line in lines[:8]:
        if any(keyword in line.lower() for keyword in TITLE_KEYWORDS):
            chunks = re.split(r"\bat\b|\bwith\b|\bfor\b", line, maxsplit=1, flags=re.IGNORECASE)
            title = _clean_candidate_value(chunks[0])
            if 2 <= len(title) <= 80:
                return title
    return None


def _extract_location(text: str) -> Optional[str]:
    lowered = text.lower()
    if any(phrase in lowered for phrase in REMOTE_LOCATION_PHRASES):
        return "Remote"
    return None


def _extract_received_datetime(msg: dict[str, Any]) -> Optional[datetime]:
    internal_date = msg.get("internalDate")
    if not internal_date:
        return None
    try:
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def _single_message_link(links: list[str]) -> Optional[str]:
    return links[0] if len(links) == 1 else None


def _status_for_label(label: GmailMessageClassification) -> Optional[str]:
    mapping = {
        "NEW_APPLICATION": "Applied",
        "INTERVIEW": "Interview",
        "REJECTION": "Rejected",
        "OFFER": "Offer",
    }
    return mapping.get(label)


def extract_email_features(msg: dict[str, Any]) -> dict[str, Any]:
    headers = _get_message_headers(msg)
    from_header = headers.get("from", "")
    email_address = _extract_email_address(from_header)
    subject = headers.get("subject", "") or ""
    snippet = msg.get("snippet", "") or ""
    raw_body_text = _extract_raw_message_body(msg.get("payload", {}))
    links = _extract_links(f"{snippet}\n{raw_body_text}")
    body_text = _extract_message_body(msg.get("payload", {}))
    fallback_text = _clean_body_text(snippet or subject)
    effective_body_text = body_text or fallback_text
    return {
        "gmail_message_id": msg.get("id", ""),
        "thread_id": msg.get("threadId"),
        "from_header": from_header,
        "from_email": email_address,
        "from_domain": _domain_from_email(email_address),
        "subject": subject,
        "date": _extract_received_datetime(msg),
        "snippet": snippet,
        "body_text": effective_body_text,
        "links": links,
        "content": _normalize_whitespace(effective_body_text).lower(),
        "first_sentence": _first_sentence(effective_body_text),
    }


def detect_source(features: dict[str, Any]) -> GmailSource:
    from_domain = features["from_domain"]
    links = features["links"]
    if "myworkday.com" in from_domain or any("myworkday.com" in _domain_from_url(link) for link in links):
        return "workday"
    if "greenhouse" in from_domain or any("greenhouse.io" in _domain_from_url(link) for link in links):
        return "greenhouse"
    if "lever" in from_domain or any("lever.co" in _domain_from_url(link) for link in links):
        return "lever"
    if "linkedin" in from_domain:
        return "linkedin"
    if "indeed" in from_domain:
        return "indeed"
    if from_domain and from_domain not in GENERIC_EMAIL_DOMAINS:
        return "company_email"
    return "unknown"


def classify_email(features: dict[str, Any]) -> GmailClassificationResult:
    content = features["content"]
    from_domain = features["from_domain"]

    if any(term in from_domain for term in THIRD_PARTY_PLATFORM_DOMAINS):
        return GmailClassificationResult(
            label="IRRELEVANT",
            confidence=0.98,
            reasons=["excluded_sender_platform"],
        )

    negative_matches = [term for term in PROMO_TERMS if term in content]
    if negative_matches and not any(phrase in content for phrase in OFFER_PHRASES + REJECTION_PHRASES + INTERVIEW_PHRASES):
        return GmailClassificationResult(
            label="IRRELEVANT",
            confidence=0.95,
            reasons=[f"promo_term:{term}" for term in negative_matches],
        )

    offer_matches = [phrase for phrase in OFFER_PHRASES if phrase in content]
    if offer_matches:
        return GmailClassificationResult(
            label="OFFER",
            confidence=0.96,
            reasons=[f"offer_phrase:{phrase}" for phrase in offer_matches],
        )

    rejection_matches = [phrase for phrase in REJECTION_PHRASES if phrase in content]
    if rejection_matches:
        return GmailClassificationResult(
            label="REJECTION",
            confidence=0.96,
            reasons=[f"rejection_phrase:{phrase}" for phrase in rejection_matches],
        )

    interview_matches = [phrase for phrase in INTERVIEW_PHRASES if phrase in content]
    if interview_matches:
        return GmailClassificationResult(
            label="INTERVIEW",
            confidence=0.92,
            reasons=[f"interview_phrase:{phrase}" for phrase in interview_matches],
        )

    update_matches = [phrase for phrase in APPLICATION_UPDATE_PHRASES if phrase in content]
    broader_update_matches = [phrase for phrase in BROADER_UPDATE_PHRASES if phrase in content]
    has_job_context = any(term in content for term in JOB_CONTEXT_TERMS)
    if update_matches:
        return GmailClassificationResult(
            label="APPLICATION_UPDATE",
            confidence=0.93,
            reasons=[f"application_update_phrase:{phrase}" for phrase in update_matches],
        )
    if broader_update_matches and has_job_context:
        return GmailClassificationResult(
            label="APPLICATION_UPDATE",
            confidence=0.8,
            reasons=[f"broader_update_phrase:{phrase}" for phrase in broader_update_matches],
        )

    confirmation_matches = [phrase for phrase in NEW_APPLICATION_PHRASES if phrase in content]
    if confirmation_matches and has_job_context:
        return GmailClassificationResult(
            label="NEW_APPLICATION",
            confidence=0.94,
            reasons=[f"confirmation_phrase:{phrase}" for phrase in confirmation_matches],
        )

    alert_matches = [phrase for phrase in JOB_ALERT_PHRASES if phrase in content]
    if alert_matches:
        return GmailClassificationResult(
            label="JOB_ALERT",
            confidence=0.88,
            reasons=[f"job_alert_phrase:{phrase}" for phrase in alert_matches],
        )

    if has_job_context:
        return GmailClassificationResult(
            label="UNKNOWN",
            confidence=0.45,
            reasons=["weak_job_context"],
        )

    return GmailClassificationResult(
        label="IRRELEVANT",
        confidence=0.9,
        reasons=["no_job_signal"],
    )


def extract_title_candidates(features: dict[str, Any]) -> list[GmailCandidate]:
    candidates: list[GmailCandidate] = []
    extraction_text = features["body_text"]
    for title, source, confidence in _extract_title_texts(extraction_text):
        _add_candidate(candidates, title, confidence, source)

    keyword_title = _extract_title_keyword_phrase(features["first_sentence"])
    _add_candidate(candidates, keyword_title, 0.72, "first_sentence_keyword")
    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)


def extract_company_candidates(features: dict[str, Any]) -> list[GmailCandidate]:
    candidates: list[GmailCandidate] = []
    sender_company = _company_from_sender(features["from_header"])
    _add_candidate(candidates, sender_company, 0.86, "sender")

    text_company = _company_from_text(features["body_text"])
    _add_candidate(candidates, text_company, 0.8, "body_phrase")

    first_sentence_company = _company_from_text(features["first_sentence"])
    _add_candidate(candidates, first_sentence_company, 0.72, "first_sentence")

    for link in features["links"]:
        domain = _domain_from_url(link)
        if domain.endswith(".myworkday.com"):
            company = domain[: -len(".myworkday.com")].split(".")[-1]
            _add_candidate(candidates, company.replace("-", " ").replace("_", " ").title(), 0.84, "workday_link")
        elif "greenhouse.io" in domain:
            path_parts = [part for part in urlparse(link).path.split("/") if part]
            if path_parts:
                _add_candidate(candidates, path_parts[0].replace("-", " ").title(), 0.76, "greenhouse_link")
        elif "lever.co" in domain:
            path_parts = [part for part in urlparse(link).path.split("/") if part]
            if path_parts:
                _add_candidate(candidates, path_parts[0].replace("-", " ").title(), 0.76, "lever_link")

    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)


def extract_location_candidates(features: dict[str, Any]) -> list[GmailCandidate]:
    candidates: list[GmailCandidate] = []
    _add_candidate(
        candidates,
        _extract_location(features["body_text"]),
        0.82,
        "explicit_remote_phrase",
    )
    return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)


def extract_identifier_candidates(features: dict[str, Any]) -> GmailIdentifierCandidates:
    identifiers = GmailIdentifierCandidates()

    if features["thread_id"]:
        identifiers.gmail_thread_id.append(
            GmailCandidate(value=str(features["thread_id"]), confidence=1.0, source="gmail_thread")
        )

    return identifiers


def choose_best_candidate(candidates: list[GmailCandidate], minimum_confidence: float = 0.5) -> Optional[GmailCandidate]:
    if not candidates:
        return None
    best = max(candidates, key=lambda candidate: candidate.confidence)
    if best.confidence < minimum_confidence:
        return None
    return best


def parse_workday(features: dict[str, Any]) -> dict[str, list[GmailCandidate]]:
    return {
        "title": extract_title_candidates(features),
        "company": extract_company_candidates(features),
        "location": extract_location_candidates(features),
    }


def parse_greenhouse(features: dict[str, Any]) -> dict[str, list[GmailCandidate]]:
    return {
        "title": extract_title_candidates(features),
        "company": extract_company_candidates(features),
        "location": extract_location_candidates(features),
    }


def parse_lever(features: dict[str, Any]) -> dict[str, list[GmailCandidate]]:
    return {
        "title": extract_title_candidates(features),
        "company": extract_company_candidates(features),
        "location": extract_location_candidates(features),
    }


def parse_generic_company_email(features: dict[str, Any]) -> dict[str, list[GmailCandidate]]:
    return {
        "title": extract_title_candidates(features),
        "company": extract_company_candidates(features),
        "location": extract_location_candidates(features),
    }


def _build_extraction_candidates(
    features: dict[str, Any],
    source: GmailSource,
) -> GmailExtractionCandidates:
    parser = {
        "workday": parse_workday,
        "greenhouse": parse_greenhouse,
        "lever": parse_lever,
    }.get(source, parse_generic_company_email)
    parsed = parser(features)
    return GmailExtractionCandidates(
        title=parsed["title"],
        company=parsed["company"],
        location=parsed["location"],
        identifiers=extract_identifier_candidates(features),
    )


def _extract_identifier_value(
    identifiers: GmailIdentifierCandidates,
    field_name: str,
) -> Optional[str]:
    return choose_best_candidate(getattr(identifiers, field_name)).value if getattr(identifiers, field_name) else None


def score_match_candidate(
    job: Any,
    identifiers: GmailIdentifierCandidates,
    best_title: Optional[str],
    best_company: Optional[str],
) -> Optional[GmailMatchCandidate]:
    thread_id = _extract_identifier_value(identifiers, "gmail_thread_id")

    if thread_id and getattr(job, "gmail_thread_id", None) == thread_id:
        return GmailMatchCandidate(
            job_id=job.id,
            company=job.company,
            title=job.title,
            status=job.status,
            match_level="thread",
            match_score=1.0,
            match_reasons=["matched_gmail_thread_id"],
            requires_review=False,
        )

    normalized_job_company = _normalize_comparison(getattr(job, "company", None))
    normalized_job_title = _normalize_comparison(getattr(job, "title", None))
    normalized_company = _normalize_comparison(best_company)
    normalized_title = _normalize_comparison(best_title)

    if normalized_company and normalized_title and normalized_job_company == normalized_company and normalized_job_title == normalized_title:
        return GmailMatchCandidate(
            job_id=job.id,
            company=job.company,
            title=job.title,
            status=job.status,
            match_level="company_title",
            match_score=0.84,
            match_reasons=["matched_company", "matched_title"],
            requires_review=False,
        )
    return None


def find_existing_job_matches(
    identifiers: GmailIdentifierCandidates,
    existing_jobs: list[Any],
    best_title: Optional[str],
    best_company: Optional[str],
) -> list[GmailMatchCandidate]:
    if not existing_jobs:
        return []

    matches = [
        score_match_candidate(job, identifiers, best_title, best_company)
        for job in existing_jobs
    ]
    filtered = [match for match in matches if match is not None]
    return sorted(
        filtered,
        key=lambda match: ({"thread": 2, "company_title": 1}[match.match_level], match.match_score),
        reverse=True,
    )


def parse_gmail_message(msg: dict[str, Any], existing_jobs: Optional[list[Any]] = None) -> GmailParsedMessageReview:
    features = extract_email_features(msg)
    source = detect_source(features)
    classification = classify_email(features)
    extraction_candidates = _build_extraction_candidates(features, source)

    best_title_candidate = choose_best_candidate(extraction_candidates.title)
    best_company_candidate = choose_best_candidate(extraction_candidates.company)
    best_location_candidate = choose_best_candidate(extraction_candidates.location, minimum_confidence=0.7)
    identifiers = extraction_candidates.identifiers

    best_title = best_title_candidate.value if best_title_candidate else None
    best_company = best_company_candidate.value if best_company_candidate else None
    best_location = best_location_candidate.value if best_location_candidate else None
    thread_id = _extract_identifier_value(identifiers, "gmail_thread_id") or features["thread_id"]
    selected_job_link = _single_message_link(features["links"])

    job_draft: Optional[GmailJobDraft] = None
    update_items: Optional[GmailUpdateItems] = None
    message_date = features["date"].date() if features["date"] else None

    if classification.label == "NEW_APPLICATION":
        job_draft = GmailJobDraft(
            title=best_title,
            company=best_company,
            location=best_location,
            job_description=None,
            applied_date=message_date,
            follow_up_date=None,
            resume_path=None,
            status="Applied",
            job_board_id=None,
            job_link=selected_job_link,
            source="Gmail",
            notes="Imported from Gmail. Review before saving.",
            gmail_thread_id=thread_id,
        )
    elif classification.label in {"APPLICATION_UPDATE", "INTERVIEW", "REJECTION", "OFFER"}:
        update_items = GmailUpdateItems(
            status=_status_for_label(classification.label),
            follow_up_date=message_date,
            job_link=selected_job_link,
            job_board_id=None,
            company=best_company,
            title=best_title,
            notes="Imported from Gmail update. Review before applying to an existing job.",
            gmail_thread_id=thread_id,
        )

    match_candidates = find_existing_job_matches(
        identifiers=identifiers,
        existing_jobs=existing_jobs or [],
        best_title=best_title,
        best_company=best_company,
    )
    best_match = match_candidates[0] if match_candidates else None

    return GmailParsedMessageReview.model_validate(
        {
            "gmail_message_id": features["gmail_message_id"],
            "thread_id": thread_id,
            "from": features["from_email"],
            "subject": features["subject"],
            "date": features["date"],
            "source": source,
            "email_content": GmailEmailContent(
                snippet=features["snippet"],
                body_text=features["body_text"],
                from_email=features["from_email"],
                from_domain=features["from_domain"],
            ),
            "classification": classification,
            "job_draft": job_draft,
            "update_items": update_items,
            "extraction_candidates": extraction_candidates,
            "match_candidates": match_candidates,
            "best_match": best_match,
            "needs_review": True,
        }
    )
