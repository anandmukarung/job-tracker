import base64
import json
import threading
from datetime import date, timedelta
from typing import Optional
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..crud import crud
from ..db.database import SessionLocal, get_db
from ..schemas.schemas import (
    GmailJobDraft,
    GmailImportCommitRequest,
    GmailImportCommitResponse,
    GmailImportCommitResult,
    GmailImportPreviewResponse,
    GmailImportPreviewStartResponse,
    GmailJobsReviewResponse,
    GmailParsedMessageReview,
    JobCreate,
    JobUpdate,
)
from ..services.email_parser import is_likely_job_email, parse_gmail_message
from ..services.gmail_client import (
    build_gmail_date_query,
    get_authorize_url,
    exchange_code_and_save_tokens,
    fetch_job_applications_from_gmail,
    get_gmail_service,
    get_message_with_service,
    get_message_metadata_with_service,
    get_valid_credentials,
    list_message_ids_with_service,
    load_credentials,
    resolve_redirect_uri,
)

router = APIRouter(prefix="/gmail", tags=["Gmail"])
callback_router = APIRouter(tags=["Gmail"])
FRONTEND_REDIRECT_WHITELIST = {"http://127.0.0.1:5173", "http://localhost:5173"}


def _session_factory():
    return SessionLocal


def _gmail_redirect_uri(request: Request) -> str:
    return resolve_redirect_uri(str(request.url_for("gmail_callback")))


def _encode_oauth_state(frontend_redirect: str) -> str:
    return base64.urlsafe_b64encode(
        json.dumps({"frontend_redirect": frontend_redirect}).encode("utf-8")
    ).decode("utf-8")


def _decode_oauth_state(state: Optional[str]) -> Optional[str]:
    if not state:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8"))
    except Exception:
        return None
    frontend_redirect = payload.get("frontend_redirect")
    if not isinstance(frontend_redirect, str):
        return None
    parsed = urlparse(frontend_redirect)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in FRONTEND_REDIRECT_WHITELIST:
        return None
    return frontend_redirect


def _default_selected_action(review: GmailParsedMessageReview) -> str:
    if review.update_items is not None and review.best_match is None:
        return "create"
    if review.job_draft is not None:
        return "create"
    if review.update_items is not None and review.best_match is not None:
        return "update"
    return "skip"


def _with_import_state(
    review: GmailParsedMessageReview,
    *,
    import_item_id: Optional[int],
    import_status: Optional[str],
    selected_action: Optional[str],
    linked_job_id: Optional[int],
    already_processed: bool,
) -> GmailParsedMessageReview:
    return review.model_copy(
        update={
            "import_item_id": import_item_id,
            "import_status": import_status,
            "selected_action": selected_action,
            "linked_job_id": linked_job_id,
            "already_processed": already_processed,
        }
    )


def _review_from_cached_payload(payload_json: str) -> Optional[GmailParsedMessageReview]:
    try:
        return GmailParsedMessageReview.model_validate(json.loads(payload_json))
    except Exception:
        return None


def _load_preview_reviews(session: object) -> list[GmailParsedMessageReview]:
    preview_payload_json = getattr(session, "preview_payload_json", None)
    if not preview_payload_json:
        return []
    try:
        payload = json.loads(preview_payload_json)
    except json.JSONDecodeError:
        return []
    return [GmailParsedMessageReview.model_validate(item) for item in payload]


def _review_in_date_range(review: GmailParsedMessageReview, start_date: date, end_date: date) -> bool:
    if review.date is None:
        return True
    review_day = review.date.date()
    return start_date <= review_day <= end_date


def _collect_cached_reviews_for_range(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> list[GmailParsedMessageReview]:
    overlapping_sessions = crud.find_completed_gmail_import_sessions_overlapping(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    reviews_by_message_id: dict[str, GmailParsedMessageReview] = {}
    for cached_session in overlapping_sessions:
        for review in _load_preview_reviews(cached_session):
            if not _review_in_date_range(review, start_date, end_date):
                continue
            reviews_by_message_id.setdefault(review.gmail_message_id, review)
    return list(reviews_by_message_id.values())


def _merge_date_ranges(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for current_start, current_end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end + timedelta(days=1):
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


def _compute_missing_date_ranges(
    *,
    start_date: date,
    end_date: date,
    covered_ranges: list[tuple[date, date]],
) -> list[tuple[date, date]]:
    if not covered_ranges:
        return [(start_date, end_date)]

    missing: list[tuple[date, date]] = []
    cursor = start_date
    for covered_start, covered_end in _merge_date_ranges(covered_ranges):
        if covered_end < start_date or covered_start > end_date:
            continue
        normalized_start = max(covered_start, start_date)
        normalized_end = min(covered_end, end_date)
        if cursor < normalized_start:
            missing.append((cursor, normalized_start - timedelta(days=1)))
        cursor = max(cursor, normalized_end + timedelta(days=1))
        if cursor > end_date:
            break
    if cursor <= end_date:
        missing.append((cursor, end_date))
    return missing


def _covered_ranges_for_reviews(
    sessions: list[object],
    *,
    start_date: date,
    end_date: date,
) -> list[tuple[date, date]]:
    covered_ranges: list[tuple[date, date]] = []
    for session in sessions:
        session_start = max(getattr(session, "start_date"), start_date)
        session_end = min(getattr(session, "end_date"), end_date)
        if session_start <= session_end:
            covered_ranges.append((session_start, session_end))
    return _merge_date_ranges(covered_ranges)


def _hydrate_cached_review(review: GmailParsedMessageReview, import_item: object) -> GmailParsedMessageReview:
    return _with_import_state(
        review,
        import_item_id=getattr(import_item, "id", None),
        import_status=getattr(import_item, "import_status", None),
        selected_action=getattr(import_item, "selected_action", None),
        linked_job_id=getattr(import_item, "linked_job_id", None),
        already_processed=getattr(import_item, "import_status", None) in {"imported", "skipped"},
    )


def _decorate_review_from_import_item(
    review: GmailParsedMessageReview,
    import_item: Optional[object],
    *,
    existing_job_ids: set[int],
) -> GmailParsedMessageReview:
    if import_item is None:
        return review

    linked_job_id = getattr(import_item, "linked_job_id", None)
    import_status = getattr(import_item, "import_status", None)
    already_processed = import_status == "skipped" or (
        import_status == "imported" and (linked_job_id is None or linked_job_id in existing_job_ids)
    )
    return _with_import_state(
        review,
        import_item_id=getattr(import_item, "id", None),
        import_status=import_status,
        selected_action=getattr(import_item, "selected_action", None),
        linked_job_id=linked_job_id,
        already_processed=already_processed,
    )


def _should_display_review(review: GmailParsedMessageReview) -> bool:
    if review.import_status == "skipped":
        return False
    if review.import_status == "imported" and review.linked_job_id is not None and review.already_processed:
        return False
    return True


def _create_fallback_job_draft(review: GmailParsedMessageReview) -> GmailParsedMessageReview:
    if review.job_draft is not None or review.update_items is None or review.best_match is not None:
        return review

    fallback_date = review.update_items.follow_up_date or (review.date.date() if review.date else None)
    fallback_draft = GmailJobDraft(
        title=review.update_items.title,
        company=review.update_items.company,
        location="Unknown",
        applied_date=fallback_date,
        follow_up_date=review.update_items.follow_up_date,
        status=review.update_items.status or "Applied",
        source="Gmail",
        notes="Created from Gmail update with no linked posting. Review before saving.",
        gmail_thread_id=review.update_items.gmail_thread_id or review.thread_id,
    )
    return review.model_copy(update={"job_draft": fallback_draft})


def _run_gmail_preview_job(session_id: int, start_date: date, end_date: date) -> None:
    db = _session_factory()()
    try:
        session = crud.get_gmail_import_session(db, session_id)
        if session is None:
            return

        crud.update_gmail_import_session(
            db,
            session,
            status="processing",
            preview_payload=[],
            error_message=None,
            total_emails=0,
            new_items=0,
        )

        existing_jobs = crud.get_jobs(db, skip=0, limit=1000)
        service = get_gmail_service()
        overlapping_sessions = crud.find_completed_gmail_import_sessions_overlapping(
            db,
            start_date=start_date,
            end_date=end_date,
        )
        covered_ranges = _covered_ranges_for_reviews(
            overlapping_sessions,
            start_date=start_date,
            end_date=end_date,
        )
        missing_ranges = _compute_missing_date_ranges(
            start_date=start_date,
            end_date=end_date,
            covered_ranges=covered_ranges,
        )

        hydrated_jobs_by_message_id = {
            review.gmail_message_id: review
            for review in _collect_cached_reviews_for_range(
                db,
                start_date=start_date,
                end_date=end_date,
            )
        }
        cached_items_count = len(hydrated_jobs_by_message_id)
        new_items = 0
        seen_message_ids: set[str] = set(hydrated_jobs_by_message_id)

        message_ids: list[str] = []
        for missing_start, missing_end in missing_ranges:
            query = build_gmail_date_query(missing_start, missing_end)
            message_ids.extend(list_message_ids_with_service(service, q=query, max_results=200))

        cached_items = {
            item.gmail_message_id: item
            for item in crud.get_gmail_import_items_by_message_ids(db, message_ids)
        }

        for message_id in message_ids:
            if message_id in seen_message_ids:
                continue
            seen_message_ids.add(message_id)
            existing_item = cached_items.get(message_id)
            cached_review = (
                _review_from_cached_payload(existing_item.payload_json)
                if existing_item is not None
                else None
            )
            if cached_review is not None:
                hydrated_jobs_by_message_id[message_id] = _create_fallback_job_draft(
                    _hydrate_cached_review(cached_review, existing_item)
                )
                cached_items_count += 1
                continue

            metadata_message = get_message_metadata_with_service(service, message_id)
            if not is_likely_job_email(metadata_message):
                continue
            message = get_message_with_service(service, message_id)
            parsed = _create_fallback_job_draft(parse_gmail_message(message, existing_jobs=existing_jobs))
            if parsed.classification.label == "IRRELEVANT":
                continue

            created_item = crud.create_gmail_import_item(
                db,
                session_id=session.id,
                review=parsed,
                selected_action=_default_selected_action(parsed),
            )
            cached_items[message_id] = created_item
            new_items += 1
            hydrated_jobs_by_message_id[message_id] = _with_import_state(
                parsed,
                import_item_id=created_item.id,
                import_status=created_item.import_status,
                selected_action=created_item.selected_action,
                linked_job_id=created_item.linked_job_id,
                already_processed=False,
            )

        hydrated_jobs = list(hydrated_jobs_by_message_id.values())
        hydrated_jobs.sort(key=lambda item: item.date or 0, reverse=True)
        crud.update_gmail_import_session(
            db,
            session,
            status="completed",
            total_emails=len(hydrated_jobs),
            new_items=new_items,
            cached_items=cached_items_count,
            cache_hit=cached_items_count > 0 and new_items == 0,
            preview_payload=hydrated_jobs,
            error_message=None,
        )
    except Exception as exc:
        db.rollback()
        session = crud.get_gmail_import_session(db, session_id)
        if session is not None:
            crud.update_gmail_import_session(
                db,
                session,
                status="failed",
                preview_payload=[],
                error_message=f"Failed to fetch Gmail import preview: {str(exc)}",
            )
    finally:
        db.close()


def launch_gmail_preview_job(session_id: int, start_date: date, end_date: date) -> None:
    worker = threading.Thread(
        target=_run_gmail_preview_job,
        args=(session_id, start_date, end_date),
        daemon=True,
    )
    worker.start()

# Generate authorization URL
@router.get("/auth/url")
def get_auth_url(request: Request, frontend_redirect: Optional[str] = None):
    """
    Generates a Google OAuth URL for the user to grant Gmail access.
    """
    redirect_uri = _gmail_redirect_uri(request)
    try:
        state = _encode_oauth_state(frontend_redirect) if frontend_redirect else None
        url = get_authorize_url(redirect_uri, state=state)
        return {"auth_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _handle_gmail_callback(request: Request, code: str, state: Optional[str] = None):
    """
    Handles OAuth callback after the user authorizes the app.
    Exchanges code for token and saves credentials.json.
    """
    redirect_uri = _gmail_redirect_uri(request)
    try:
        creds = exchange_code_and_save_tokens(code, redirect_uri)
        frontend_redirect = _decode_oauth_state(state)
        if frontend_redirect:
            separator = "&" if "?" in frontend_redirect else "?"
            return RedirectResponse(url=f"{frontend_redirect}{separator}{urlencode({'gmail': 'connected'})}")
        return {"message": "Authorization successful!", "credentials": creds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth failed: {str(e)}")


# Callback endpoint for OAuth
@router.get("/auth/callback", name="gmail_callback")
def gmail_callback(request: Request, code: str, state: Optional[str] = None):
    return _handle_gmail_callback(request, code, state)


@callback_router.get("/external/auth/callback")
def gmail_callback_alias(request: Request, code: str, state: Optional[str] = None):
    return _handle_gmail_callback(request, code, state)


# Check connection status
@router.get("/status")
def gmail_status():
    """
    Checks whether valid Gmail credentials are available.
    """
    creds = load_credentials()
    if creds is None:
        return {"authorized": False, "message": "No credentials found."}
    try:
        valid_creds = get_valid_credentials()
    except Exception as exc:
        return {
            "authorized": False,
            "message": "Stored Gmail credentials need to be re-authorized.",
            "requires_reauth": True,
            "detail": str(exc),
        }
    return {"authorized": True, "token_expired": not valid_creds.valid}


# Fetch job candidates
@router.get("/jobs", response_model=GmailJobsReviewResponse)
def get_jobs_from_gmail(
    query: str = Query(
        "applied OR 'thank you for your application' newer_than:365d",
        description="Gmail search query to filter job-related emails",
    ),
    max_results: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Fetch job application emails and parse possible job candidates.
    """
    try:
        existing_jobs = crud.get_jobs(db, skip=0, limit=1000)
        jobs = fetch_job_applications_from_gmail(
            query=query,
            max_results=max_results,
            existing_jobs=existing_jobs,
        )
        return {"count": len(jobs), "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail jobs: {str(e)}")


@router.post("/import/preview", response_model=GmailImportPreviewStartResponse)
def start_gmail_import_preview(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
):
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    overlapping_sessions = crud.find_completed_gmail_import_sessions_overlapping(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    covered_ranges = _covered_ranges_for_reviews(
        overlapping_sessions,
        start_date=start_date,
        end_date=end_date,
    )
    cached_reviews = _collect_cached_reviews_for_range(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    if not _compute_missing_date_ranges(
        start_date=start_date,
        end_date=end_date,
        covered_ranges=covered_ranges,
    ):
        session = crud.create_gmail_import_session(
            db,
            start_date=start_date,
            end_date=end_date,
            status="completed",
        )
        session = crud.update_gmail_import_session(
            db,
            session,
            status="completed",
            total_emails=len(cached_reviews),
            new_items=0,
            cached_items=len(cached_reviews),
            cache_hit=True,
            preview_payload=cached_reviews,
            error_message=None,
        )
        return {"session": session}

    session = crud.create_gmail_import_session(
        db,
        start_date=start_date,
        end_date=end_date,
        status="queued",
    )
    launch_gmail_preview_job(session.id, start_date, end_date)
    return {"session": session}


@router.get("/import/preview/{session_id}", response_model=GmailImportPreviewResponse)
def get_gmail_import_preview(
    session_id: int,
    db: Session = Depends(get_db),
):
    session = crud.get_gmail_import_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Import session not found")

    jobs: list[GmailParsedMessageReview] = []
    if session.status == "completed":
        existing_job_ids = {job.id for job in crud.get_jobs(db, skip=0, limit=5000)}
        hydrated_reviews: list[GmailParsedMessageReview] = []
        for review in _load_preview_reviews(session):
            import_item = crud.get_gmail_import_item_by_message_id(db, review.gmail_message_id)
            hydrated_review = _decorate_review_from_import_item(
                review,
                import_item,
                existing_job_ids=existing_job_ids,
            )
            if _should_display_review(hydrated_review):
                hydrated_reviews.append(hydrated_review)
        jobs = hydrated_reviews
    return {"session": session, "count": len(jobs), "jobs": jobs}


@router.post("/import/commit", response_model=GmailImportCommitResponse)
def commit_gmail_import(
    payload: GmailImportCommitRequest,
    db: Session = Depends(get_db),
):
    session = crud.get_gmail_import_session(db, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Import session not found")
    preview_reviews = {
        review.gmail_message_id: review
        for review in _load_preview_reviews(session)
    }

    imported_count = skipped_count = failed_count = 0
    results: list[GmailImportCommitResult] = []

    for selection in payload.items:
        if selection.gmail_message_id not in preview_reviews:
            results.append(
                GmailImportCommitResult(
                    gmail_message_id=selection.gmail_message_id,
                    action=selection.action,
                    status="failed",
                    error="Import item not found in preview session",
                )
            )
            failed_count += 1
            continue

        item = crud.get_gmail_import_item_by_session_and_message_id(
            db,
            session_id=payload.session_id,
            gmail_message_id=selection.gmail_message_id,
        )
        if item is None:
            item = crud.get_gmail_import_item_by_message_id(db, selection.gmail_message_id)
        if item is None:
            results.append(
                GmailImportCommitResult(
                    gmail_message_id=selection.gmail_message_id,
                    action=selection.action,
                    status="failed",
                    error="Import item not found in cache",
                )
            )
            failed_count += 1
            continue

        try:
            linked_job_id: Optional[int] = None
            if selection.action == "skip":
                crud.update_gmail_import_item(
                    db,
                    item,
                    payload=selection.model_dump(mode="json"),
                    selected_action="skip",
                    import_status="skipped",
                    linked_job_id=None,
                    failure_reason=None,
                )
                skipped_count += 1
                results.append(
                    GmailImportCommitResult(
                        gmail_message_id=selection.gmail_message_id,
                        action="skip",
                        status="skipped",
                    )
                )
                continue

            if selection.action == "create":
                draft_source = selection.job_draft
                if draft_source is None and selection.update_items is not None:
                    draft_source = JobCreate(
                        title=selection.update_items.title or "Unknown title",
                        company=selection.update_items.company or "Unknown company",
                        location="Unknown",
                        status=selection.update_items.status or "Applied",
                        applied_date=selection.update_items.follow_up_date,
                        follow_up_date=selection.update_items.follow_up_date,
                        source="Gmail",
                        notes=selection.update_items.notes,
                        gmail_thread_id=selection.update_items.gmail_thread_id,
                    )
                if draft_source is None:
                    raise ValueError("job_draft is required for create actions")
                draft_payload = draft_source.model_dump(exclude_none=True) if hasattr(draft_source, "model_dump") else draft_source.dict(exclude_none=True)
                draft_payload["title"] = draft_payload.get("title") or "Unknown title"
                draft_payload["company"] = draft_payload.get("company") or "Unknown company"
                draft_payload["location"] = draft_payload.get("location") or "Unknown"
                posting = crud.get_or_create_job_posting(
                    db,
                    company=draft_payload["company"],
                    title=draft_payload["title"],
                    source=draft_payload.get("source"),
                    notes=draft_payload.get("notes"),
                )
                existing_job = next(
                    (
                        job
                        for job in crud.get_jobs(db, skip=0, limit=1000)
                        if job.posting_id == posting.id
                    ),
                    None,
                )
                if existing_job is not None:
                    update_payload = {}
                    if not existing_job.applied_date and draft_payload.get("applied_date"):
                        update_payload["applied_date"] = draft_payload["applied_date"]
                    if draft_payload.get("follow_up_date"):
                        update_payload["follow_up_date"] = draft_payload["follow_up_date"]
                    if draft_payload.get("status"):
                        update_payload["status"] = draft_payload["status"]
                    if update_payload:
                        updated_job = crud.update_job(db, existing_job.id, JobUpdate(**update_payload))
                        assert updated_job is not None
                        linked_job_id = updated_job.id
                    else:
                        linked_job_id = existing_job.id
                else:
                    created_job = crud.create_job(db, JobCreate(posting_id=posting.id, **draft_payload))
                    linked_job_id = created_job.id
            elif selection.action == "update":
                if selection.target_job_id is None:
                    if selection.update_items is None:
                        raise ValueError("update_items is required for update actions")
                    fallback_create = JobCreate(
                        title=selection.update_items.title or "Unknown title",
                        company=selection.update_items.company or "Unknown company",
                        location="Unknown",
                        status=selection.update_items.status or "Applied",
                        applied_date=selection.update_items.follow_up_date,
                        follow_up_date=selection.update_items.follow_up_date,
                        source="Gmail",
                        notes=selection.update_items.notes,
                        gmail_thread_id=selection.update_items.gmail_thread_id,
                    )
                    created_job = crud.create_job(db, fallback_create)
                    linked_job_id = created_job.id
                else:
                    if selection.update_items is None:
                        raise ValueError("update_items is required for update actions")
                    update_payload = selection.update_items.model_dump(
                        exclude_none=True,
                        exclude={"company", "title"},
                    )
                    updated_job = crud.update_job(db, selection.target_job_id, JobUpdate(**update_payload))
                    if updated_job is None:
                        raise ValueError("Target job not found")
                    linked_job_id = updated_job.id
            else:
                raise ValueError("Unsupported action")

            crud.update_gmail_import_item(
                db,
                item,
                payload=selection.model_dump(mode="json"),
                selected_action=selection.action,
                import_status="imported",
                linked_job_id=linked_job_id,
                failure_reason=None,
            )
            imported_count += 1
            results.append(
                GmailImportCommitResult(
                    gmail_message_id=selection.gmail_message_id,
                    action=selection.action,
                    status="imported",
                    linked_job_id=linked_job_id,
                )
            )
        except Exception as exc:
            crud.update_gmail_import_item(
                db,
                item,
                payload=selection.model_dump(mode="json"),
                selected_action=selection.action,
                import_status="failed",
                linked_job_id=item.linked_job_id,
                failure_reason=str(exc),
            )
            failed_count += 1
            results.append(
                GmailImportCommitResult(
                    gmail_message_id=selection.gmail_message_id,
                    action=selection.action,
                    status="failed",
                    linked_job_id=item.linked_job_id,
                    error=str(exc),
                )
            )

    session = crud.update_gmail_import_session(
        db,
        session,
        status="completed",
        imported_items=session.imported_items + imported_count,
        skipped_items=session.skipped_items + skipped_count,
        failed_items=session.failed_items + failed_count,
    )
    return {"session": session, "results": results}
