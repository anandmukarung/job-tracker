import json
from datetime import date
import re
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Optional

from ..models import models
from ..schemas import schemas


def _normalize_identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def get_or_create_job_posting(
    db: Session,
    *,
    company: str,
    title: str,
    source: Optional[str] = None,
    notes: Optional[str] = None,
) -> models.JobPosting:
    normalized_company = _normalize_identity(company)
    normalized_title = _normalize_identity(title)
    posting = (
        db.query(models.JobPosting)
        .filter(
            models.JobPosting.normalized_company == normalized_company,
            models.JobPosting.normalized_title == normalized_title,
        )
        .first()
    )
    if posting is not None:
        return posting

    posting = models.JobPosting(
        company=company,
        title=title,
        normalized_company=normalized_company,
        normalized_title=normalized_title,
        source=source,
        notes=notes,
    )
    db.add(posting)
    db.commit()
    db.refresh(posting)
    return posting


def get_job_posting_by_company_title(
    db: Session,
    *,
    company: str,
    title: str,
) -> Optional[models.JobPosting]:
    return (
        db.query(models.JobPosting)
        .filter(
            models.JobPosting.normalized_company == _normalize_identity(company),
            models.JobPosting.normalized_title == _normalize_identity(title),
        )
        .first()
    )


def search_company_suggestions(db: Session, query: str, limit: int = 10) -> list[str]:
    postings = (
        db.query(models.JobPosting.company)
        .filter(models.JobPosting.company.ilike(f"%{query}%"))
        .distinct()
        .order_by(models.JobPosting.company.asc())
        .limit(limit)
        .all()
    )
    return [company for (company,) in postings]


def search_job_postings(
    db: Session,
    *,
    company: str,
    query: Optional[str] = None,
    limit: int = 20,
) -> list[models.JobPosting]:
    postings_query = db.query(models.JobPosting).filter(models.JobPosting.company == company)
    if query:
        postings_query = postings_query.filter(models.JobPosting.title.ilike(f"%{query}%"))
    return postings_query.order_by(models.JobPosting.title.asc()).limit(limit).all()


def find_latest_cached_gmail_import_session(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> Optional[models.GmailImportSession]:
    return (
        db.query(models.GmailImportSession)
        .filter(
            models.GmailImportSession.start_date == start_date,
            models.GmailImportSession.end_date == end_date,
            models.GmailImportSession.status == "completed",
            models.GmailImportSession.preview_payload_json.isnot(None),
        )
        .order_by(models.GmailImportSession.updated_at.desc())
        .first()
    )


def find_completed_gmail_import_sessions_overlapping(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> list[models.GmailImportSession]:
    return (
        db.query(models.GmailImportSession)
        .filter(
            models.GmailImportSession.status == "completed",
            models.GmailImportSession.preview_payload_json.isnot(None),
            models.GmailImportSession.start_date <= end_date,
            models.GmailImportSession.end_date >= start_date,
        )
        .order_by(models.GmailImportSession.updated_at.desc())
        .all()
    )

def create_job(db: Session, job: schemas.JobCreate) -> models.Job:
    #Check for duplicate job posting
    if job.job_board_id and job.company:
        existing_job = db.query(models.Job).filter(
            models.Job.job_board_id == job.job_board_id,
            models.Job.company == job.company
        ).first()
        if existing_job:
            return existing_job # Return existing job instead of duplicating
    #Create new job instance
    posting = get_or_create_job_posting(
        db,
        company=job.company,
        title=job.title,
        source=job.source,
        notes=job.notes,
    )
    db_job = models.Job(
        posting_id=job.posting_id or posting.id,
        title=job.title,
        company=job.company,
        location=job.location,
        status=job.status,
        applied_date=job.applied_date,
        follow_up_date=job.follow_up_date,
        job_link=job.job_link,
        job_description=job.job_description,
        resume_path=job.resume_path,
        job_board_id=job.job_board_id,
        source=job.source,
        notes=job.notes,
        gmail_thread_id=job.gmail_thread_id,
        ats_source=job.ats_source,
        ats_requisition_id=job.ats_requisition_id,
        ats_application_id=job.ats_application_id,
        ats_candidate_id=job.ats_candidate_id,
    )
    
    #Add to session and commit
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job_by_id(db: Session, job_id: int) -> Optional[models.Job]:
    return db.query(models.Job).filter(models.Job.id == job_id).first()

def get_jobs(db: Session, skip: int = 0, limit: int = 100) -> list[models.Job]:
    return db.query(models.Job).offset(skip).limit(limit).all()


def get_job_by_gmail_thread_id(db: Session, gmail_thread_id: str) -> Optional[models.Job]:
    return db.query(models.Job).filter(models.Job.gmail_thread_id == gmail_thread_id).first()

def update_job(
    db: Session, job_id: int, job_update: schemas.JobUpdate
) -> Optional[models.Job]:
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        return None
    #Update fields if provided
    update_data = job_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_job, key, value)
    if (job_update.company or db_job.company) and (job_update.title or db_job.title):
        posting = get_or_create_job_posting(
            db,
            company=job_update.company or db_job.company,
            title=job_update.title or db_job.title,
            source=job_update.source or db_job.source,
            notes=job_update.notes or db_job.notes,
        )
        db_job.posting_id = posting.id
    db.commit()
    db.refresh(db_job)
    return db_job

def delete_job(db: Session, job_id: int) -> Optional[models.Job]:
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        return None
    db.delete(db_job)
    db.commit()
    return db_job

#Search job by company, title, location or status
def get_jobs_by_filters(
    db: Session, 
    company: Optional[str] = None,
    title: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "applied_date",
    sort_desc: bool = True
) -> list[models.Job]:
    query = db.query(models.Job)
    if company:
        query = query.filter(models.Job.company.ilike(f"%{company}%"))
    if title:
        query = query.filter(models.Job.title.ilike(f"%{title}%"))
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if status:
        query = query.filter(models.Job.status.ilike(f"%{status}%"))

    #Sorting
    if hasattr(models.Job, sort_by):
        column = getattr(models.Job, sort_by)
        if sort_desc: 
            column = column.desc()
        query = query.order_by(column)
    return query.offset(skip).limit(limit).all()


def create_gmail_import_session(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    status: str = "preview",
) -> models.GmailImportSession:
    session = models.GmailImportSession(
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_gmail_import_session(
    db: Session,
    session: models.GmailImportSession,
    *,
    status: Optional[str] = None,
    total_emails: Optional[int] = None,
    new_items: Optional[int] = None,
    imported_items: Optional[int] = None,
    skipped_items: Optional[int] = None,
    failed_items: Optional[int] = None,
    cached_items: Optional[int] = None,
    cache_hit: Optional[bool] = None,
    preview_payload: Optional[list[schemas.GmailParsedMessageReview]] = None,
    error_message: Optional[str] = None,
) -> models.GmailImportSession:
    if status is not None:
        session.status = status
    if total_emails is not None:
        session.total_emails = total_emails
    if new_items is not None:
        session.new_items = new_items
    if imported_items is not None:
        session.imported_items = imported_items
    if skipped_items is not None:
        session.skipped_items = skipped_items
    if failed_items is not None:
        session.failed_items = failed_items
    if cached_items is not None:
        session.cached_items = cached_items
    if cache_hit is not None:
        session.cache_hit = "true" if cache_hit else "false"
    if preview_payload is not None:
        session.preview_payload_json = json.dumps(
            [review.model_dump(by_alias=True, mode="json") for review in preview_payload]
        )
    session.error_message = error_message
    db.commit()
    db.refresh(session)
    return session


def get_gmail_import_session(db: Session, session_id: int) -> Optional[models.GmailImportSession]:
    return db.query(models.GmailImportSession).filter(models.GmailImportSession.id == session_id).first()


def get_gmail_import_items_by_message_ids(
    db: Session,
    gmail_message_ids: list[str],
) -> list[models.GmailImportItem]:
    if not gmail_message_ids:
        return []
    return (
        db.query(models.GmailImportItem)
        .filter(models.GmailImportItem.gmail_message_id.in_(gmail_message_ids))
        .all()
    )


def get_gmail_import_item_by_message_id(
    db: Session,
    gmail_message_id: str,
) -> Optional[models.GmailImportItem]:
    return (
        db.query(models.GmailImportItem)
        .filter(models.GmailImportItem.gmail_message_id == gmail_message_id)
        .first()
    )


def get_gmail_import_item_by_session_and_message_id(
    db: Session,
    session_id: int,
    gmail_message_id: str,
) -> Optional[models.GmailImportItem]:
    return (
        db.query(models.GmailImportItem)
        .filter(
            models.GmailImportItem.session_id == session_id,
            models.GmailImportItem.gmail_message_id == gmail_message_id,
        )
        .first()
    )


def create_gmail_import_item(
    db: Session,
    *,
    session_id: int,
    review: schemas.GmailParsedMessageReview,
    selected_action: str,
) -> models.GmailImportItem:
    existing_item = get_gmail_import_item_by_message_id(db, review.gmail_message_id)
    if existing_item is not None:
        existing_item.session_id = session_id
        existing_item.gmail_thread_id = review.thread_id
        existing_item.from_email = review.from_
        existing_item.subject = review.subject
        existing_item.message_date = review.date
        existing_item.payload_json = json.dumps(review.model_dump(by_alias=True, mode="json"))
        if existing_item.import_status == "pending":
            existing_item.selected_action = selected_action
        db.commit()
        db.refresh(existing_item)
        return existing_item

    item = models.GmailImportItem(
        session_id=session_id,
        gmail_message_id=review.gmail_message_id,
        gmail_thread_id=review.thread_id,
        from_email=review.from_,
        subject=review.subject,
        message_date=review.date,
        payload_json=json.dumps(review.model_dump(by_alias=True, mode="json")),
        selected_action=selected_action,
        import_status="pending",
    )
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError:
        db.rollback()
        existing_item = get_gmail_import_item_by_message_id(db, review.gmail_message_id)
        if existing_item is None:
            raise
        existing_item.session_id = session_id
        existing_item.gmail_thread_id = review.thread_id
        existing_item.from_email = review.from_
        existing_item.subject = review.subject
        existing_item.message_date = review.date
        existing_item.payload_json = json.dumps(review.model_dump(by_alias=True, mode="json"))
        if existing_item.import_status == "pending":
            existing_item.selected_action = selected_action
        db.commit()
        db.refresh(existing_item)
        return existing_item


def update_gmail_import_item(
    db: Session,
    item: models.GmailImportItem,
    *,
    payload: Optional[dict[str, Any]] = None,
    selected_action: Optional[str] = None,
    import_status: Optional[str] = None,
    linked_job_id: Optional[int] = None,
    failure_reason: Optional[str] = None,
) -> models.GmailImportItem:
    if payload is not None:
        item.payload_json = json.dumps(payload)
    if selected_action is not None:
        item.selected_action = selected_action
    if import_status is not None:
        item.import_status = import_status
    item.linked_job_id = linked_job_id
    item.failure_reason = failure_reason
    db.commit()
    db.refresh(item)
    return item
