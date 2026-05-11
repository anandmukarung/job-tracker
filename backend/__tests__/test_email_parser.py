import base64
from datetime import date
from types import SimpleNamespace

from backend.app.services.email_parser import (
    detect_source,
    extract_company_candidates,
    extract_email_features,
    parse_gmail_message,
)


def make_message(
    *,
    message_id: str = "msg-1",
    thread_id: str = "thread-1",
    from_value: str = "OpenAI Recruiting <jobs@openai.com>",
    subject: str = "Subject",
    body: str = "",
    snippet: str = "",
    internal_date: str = "1759276800000",
) -> dict[str, object]:
    encoded_body = base64.urlsafe_b64encode(body.encode("utf-8")).decode("utf-8")
    return {
        "id": message_id,
        "threadId": thread_id,
        "payload": {
            "headers": [
                {"name": "From", "value": from_value},
                {"name": "Subject", "value": subject},
            ],
            "body": {"data": encoded_body},
        },
        "snippet": snippet,
        "internalDate": internal_date,
    }


def test_extract_email_features_returns_normalized_fields() -> None:
    msg = make_message(
        from_value="OpenAI Recruiting <jobs@openai.com>",
        subject="Application received",
        body="<p>Thank you for applying.</p><p>https://apply.workday.com/openai/job/backend</p>",
        snippet="Thank you for applying",
    )

    features = extract_email_features(msg)

    assert features["gmail_message_id"] == "msg-1"
    assert features["thread_id"] == "thread-1"
    assert features["from_email"] == "jobs@openai.com"
    assert features["from_domain"] == "openai.com"
    assert features["subject"] == "Application received"
    assert features["snippet"] == "Thank you for applying"
    assert "Thank you for applying" in features["body_text"]
    assert "https://apply.workday.com/openai/job/backend" not in features["body_text"]
    assert features["links"] == ["https://apply.workday.com/openai/job/backend"]


def test_body_text_is_clean_plain_text_without_html_or_links() -> None:
    msg = make_message(
        body="""
        <html>
          <body>
            <p>Thank you for applying for the Backend Engineer position at OpenAI.</p>
            <p>See details at https://jobs.example.com/backend-engineer</p>
          </body>
        </html>
        """,
    )

    features = extract_email_features(msg)

    assert "<p>" not in features["body_text"]
    assert "https://jobs.example.com/backend-engineer" not in features["body_text"]
    assert "Thank you for applying for the Backend Engineer position at OpenAI." in features["body_text"]


def test_detect_source_identifies_workday_greenhouse_and_lever() -> None:
    workday = extract_email_features(
        make_message(
            from_value="noreply@company.myworkday.com",
            body="https://company.myworkday.com/en-US/recruiting/job/123",
        )
    )
    greenhouse = extract_email_features(
        make_message(
            from_value="jobs@boards.greenhouse.io",
            body="https://boards.greenhouse.io/openai/jobs/123",
        )
    )
    lever = extract_email_features(
        make_message(
            from_value="jobs@hire.lever.co",
            body="https://jobs.lever.co/openai/abc",
        )
    )
    fallback = extract_email_features(make_message(from_value="Hiring <jobs@startup.com>"))

    assert detect_source(workday) == "workday"
    assert detect_source(greenhouse) == "greenhouse"
    assert detect_source(lever) == "lever"
    assert detect_source(fallback) == "company_email"


def test_workday_company_candidate_extracts_from_sender_and_link() -> None:
    features = extract_email_features(
        make_message(
            from_value="noreply@acme.myworkday.com",
            body="Review here https://acme.myworkday.com/en-US/recruiting/job/123",
        )
    )

    candidates = extract_company_candidates(features)
    values = [candidate.value for candidate in candidates]

    assert "Acme" in values


def test_title_and_company_extraction_do_not_depend_on_order() -> None:
    company_first = make_message(
        from_value="Careers <jobs@openai.com>",
        subject="Thank you for applying to OpenAI",
        body="Thank you for applying for the Software Engineer position at OpenAI.",
        snippet="Thank you for applying for the Software Engineer position at OpenAI.",
    )
    title_first = make_message(
        from_value="Careers <jobs@openai.com>",
        subject="Software Engineer position at OpenAI",
        body="Thank you for applying to OpenAI. We received your application for the Software Engineer position.",
        snippet="We received your application for the Software Engineer position.",
    )

    company_first_parsed = parse_gmail_message(company_first)
    title_first_parsed = parse_gmail_message(title_first)

    assert company_first_parsed.job_draft is not None
    assert company_first_parsed.job_draft.company == "OpenAI"
    assert company_first_parsed.job_draft.title == "Software Engineer"
    assert title_first_parsed.job_draft is not None
    assert title_first_parsed.job_draft.company == "OpenAI"
    assert title_first_parsed.job_draft.title == "Software Engineer"


def test_subject_does_not_override_usable_body_extraction() -> None:
    msg = make_message(
        subject="Marketing Update",
        body="Thank you for applying for the Product Designer position at OpenAI.",
        snippet="Marketing Update",
    )

    parsed = parse_gmail_message(msg)

    assert parsed.job_draft is not None
    assert parsed.job_draft.title == "Product Designer"


def test_generic_confirmation_email_returns_job_draft_and_needs_review() -> None:
    msg = make_message(
        subject="Application received",
        body=(
            "Thank you for applying for the Backend Engineer position at OpenAI. "
            "Apply portal: https://jobs.lever.co/openai/backend"
        ),
        snippet="Thank you for applying for the Backend Engineer position at OpenAI.",
    )

    parsed = parse_gmail_message(msg)

    assert parsed.classification.label == "NEW_APPLICATION"
    assert parsed.job_draft is not None
    assert parsed.job_draft.title == "Backend Engineer"
    assert parsed.job_draft.company == "OpenAI"
    assert parsed.job_draft.applied_date == date(2025, 10, 1)
    assert parsed.job_draft.job_link == "https://jobs.lever.co/openai/backend"
    assert parsed.update_items is None
    assert parsed.needs_review is True


def test_job_link_is_only_included_when_exactly_one_link_exists() -> None:
    one_link = parse_gmail_message(
        make_message(
            body=(
                "Thank you for applying for the Backend Engineer position at OpenAI. "
                "Apply portal: https://jobs.lever.co/openai/backend"
            ),
        )
    )
    multiple_links = parse_gmail_message(
        make_message(
            body=(
                "Thank you for applying for the Backend Engineer position at OpenAI. "
                "Links: https://jobs.lever.co/openai/backend and https://openai.com/careers"
            ),
        )
    )

    assert one_link.job_draft is not None and one_link.job_draft.job_link == "https://jobs.lever.co/openai/backend"
    assert multiple_links.job_draft is not None and multiple_links.job_draft.job_link is None


def test_application_update_returns_update_items_not_job_draft() -> None:
    msg = make_message(
        subject="Update on your application",
        body="Update on your application for the Product Manager position at OpenAI.",
        snippet="Update on your application for the Product Manager position.",
    )

    parsed = parse_gmail_message(msg)

    assert parsed.classification.label == "APPLICATION_UPDATE"
    assert parsed.job_draft is None
    assert parsed.update_items is not None
    assert parsed.update_items.follow_up_date == date(2025, 10, 1)


def test_broader_follow_up_language_maps_to_application_update() -> None:
    msg = make_message(
        body="We are following up on your application for the Product Manager position at OpenAI with next steps.",
    )

    parsed = parse_gmail_message(msg)

    assert parsed.classification.label == "APPLICATION_UPDATE"
    assert parsed.update_items is not None


def test_interview_rejection_and_offer_map_to_update_items() -> None:
    interview = parse_gmail_message(
        make_message(
            subject="Interview scheduled",
            body="Your interview has been scheduled for the Data Scientist position at OpenAI.",
        )
    )
    rejection = parse_gmail_message(
        make_message(
            subject="Update on your application",
            body="After careful consideration, we regret to inform you that we will not move forward.",
        )
    )
    offer = parse_gmail_message(
        make_message(
            subject="Formal offer",
            body="We are pleased to offer you employment for the Platform Engineer position at OpenAI.",
        )
    )

    assert interview.classification.label == "INTERVIEW"
    assert interview.update_items is not None and interview.update_items.status == "Interview"
    assert rejection.classification.label == "REJECTION"
    assert rejection.update_items is not None and rejection.update_items.status == "Rejected"
    assert offer.classification.label == "OFFER"
    assert offer.update_items is not None and offer.update_items.status == "Offer"


def test_uncertain_extraction_returns_candidates_without_crashing() -> None:
    msg = make_message(
        from_value="Talent Team <talent@startup.com>",
        subject="About your Data Analyst application",
        body="We wanted to follow up about your Data Analyst application.",
        snippet="We wanted to follow up about your Data Analyst application.",
    )

    parsed = parse_gmail_message(msg)

    assert parsed.classification.label == "UNKNOWN"
    assert parsed.job_draft is None
    assert parsed.extraction_candidates.title
    assert parsed.email_content.body_text is not None


def test_ambiguous_recruiter_email_without_application_context_is_irrelevant() -> None:
    msg = make_message(
        from_value="Recruiter <hello@startup.com>",
        subject="Quick follow up",
        body="Just checking in to see if you are available this week.",
        snippet="Just checking in to see if you are available this week.",
    )

    parsed = parse_gmail_message(msg)

    assert parsed.classification.label == "IRRELEVANT"


def test_irrelevant_email_returns_no_job_draft() -> None:
    msg = make_message(
        from_value="GoodLeap <offers@goodleap.com>",
        subject="Special offer just for you",
        body="Limited time credit offer with a low APR.",
        snippet="Limited time credit offer.",
    )

    parsed = parse_gmail_message(msg)

    assert parsed.classification.label == "IRRELEVANT"
    assert parsed.job_draft is None
    assert parsed.update_items is None


def test_parse_gmail_message_output_shape_is_stable() -> None:
    parsed = parse_gmail_message(
        make_message(
            subject="Application received",
            body="Thank you for applying for the Data Engineer position at OpenAI.",
        )
    )

    dumped = parsed.model_dump(by_alias=True)

    assert set(dumped) == {
        "gmail_message_id",
        "thread_id",
        "from",
        "subject",
        "date",
        "source",
        "email_content",
        "classification",
        "job_draft",
        "update_items",
        "extraction_candidates",
        "match_candidates",
        "best_match",
        "needs_review",
    }


def test_matching_hierarchy_prefers_thread_then_company_title_only() -> None:
    msg = make_message(
        thread_id="gmail-thread-123",
        from_value="Careers <jobs@openai.com>",
        subject="Update on your application",
        body="Update on your application for the Backend Engineer position at OpenAI.",
    )

    existing_jobs = [
        SimpleNamespace(
            id=1,
            company="Different Co",
            title="Different Title",
            status="Applied",
            gmail_thread_id="gmail-thread-123",
            job_board_id=None,
            applied_date=date(2025, 9, 30),
        ),
        SimpleNamespace(
            id=2,
            company="OpenAI",
            title="Backend Engineer",
            status="Applied",
            gmail_thread_id=None,
            job_board_id=None,
            applied_date=date(2025, 9, 28),
        ),
    ]

    parsed = parse_gmail_message(msg, existing_jobs=existing_jobs)

    assert parsed.best_match is not None
    assert parsed.best_match.job_id == 1
    assert parsed.match_candidates[0].match_level == "thread"
    assert any(candidate.job_id == 2 and candidate.match_level == "company_title" for candidate in parsed.match_candidates)
    assert len(parsed.match_candidates) == 2
