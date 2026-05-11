from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobBase(BaseModel):
    title: str
    company: str
    location: str
    job_description: Optional[str] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    resume_path: Optional[str] = None
    status: Optional[str] = "Applied"
    job_board_id: Optional[str] = None
    job_link: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    ats_source: Optional[str] = None
    ats_requisition_id: Optional[str] = None
    ats_application_id: Optional[str] = None
    ats_candidate_id: Optional[str] = None


class JobCreate(JobBase):
    pass


class JobUpdate(JobBase):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_description: Optional[str] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    resume_path: Optional[str] = None
    status: Optional[str] = None
    job_board_id: Optional[str] = None
    job_link: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    ats_source: Optional[str] = None
    ats_requisition_id: Optional[str] = None
    ats_application_id: Optional[str] = None
    ats_candidate_id: Optional[str] = None


class Job(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


GmailSource = Literal[
    "workday",
    "greenhouse",
    "lever",
    "linkedin",
    "indeed",
    "company_email",
    "unknown",
]
GmailMessageClassification = Literal[
    "NEW_APPLICATION",
    "APPLICATION_UPDATE",
    "INTERVIEW",
    "REJECTION",
    "OFFER",
    "JOB_ALERT",
    "IRRELEVANT",
    "UNKNOWN",
]


class GmailCandidate(BaseModel):
    value: str
    confidence: float
    source: str


class GmailIdentifierCandidates(BaseModel):
    gmail_thread_id: list[GmailCandidate] = Field(default_factory=list)


class GmailEmailContent(BaseModel):
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    from_email: Optional[str] = None
    from_domain: Optional[str] = None


class GmailClassificationResult(BaseModel):
    label: GmailMessageClassification
    confidence: float
    reasons: list[str]


class GmailJobDraft(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_description: Optional[str] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    resume_path: Optional[str] = None
    status: Optional[str] = None
    job_board_id: Optional[str] = None
    job_link: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    gmail_thread_id: Optional[str] = None


class GmailUpdateItems(BaseModel):
    status: Optional[str] = None
    follow_up_date: Optional[date] = None
    job_link: Optional[str] = None
    job_board_id: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    gmail_thread_id: Optional[str] = None


class GmailExtractionCandidates(BaseModel):
    title: list[GmailCandidate] = Field(default_factory=list)
    company: list[GmailCandidate] = Field(default_factory=list)
    location: list[GmailCandidate] = Field(default_factory=list)
    identifiers: GmailIdentifierCandidates


class GmailMatchCandidate(BaseModel):
    job_id: int
    company: str
    title: str
    status: Optional[str] = None
    match_level: Literal["thread", "company_title"]
    match_score: float
    match_reasons: list[str]
    requires_review: bool


class GmailParsedMessageReview(BaseModel):
    gmail_message_id: str
    thread_id: Optional[str] = None
    from_: str = Field(alias="from")
    subject: str
    date: Optional[datetime] = None
    source: GmailSource
    email_content: GmailEmailContent
    classification: GmailClassificationResult
    job_draft: Optional[GmailJobDraft] = None
    update_items: Optional[GmailUpdateItems] = None
    extraction_candidates: GmailExtractionCandidates
    match_candidates: list[GmailMatchCandidate] = Field(default_factory=list)
    best_match: Optional[GmailMatchCandidate] = None
    needs_review: bool = True

    model_config = ConfigDict(populate_by_name=True)


class GmailJobsReviewResponse(BaseModel):
    count: int
    jobs: list[GmailParsedMessageReview]
