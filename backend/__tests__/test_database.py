from datetime import date

from backend.app.crud import crud
from backend.app.schemas import schemas


def test_create_job_persists_job_description(db_session):
    job = schemas.JobCreate(
        title="Software Engineer",
        company="OpenAI",
        location="Remote",
        status="Applied",
        job_description="Build product features",
        job_board_id="oa-123",
        source="LinkedIn",
    )

    created = crud.create_job(db_session, job)

    assert created.id is not None
    assert created.job_description == "Build product features"


def test_create_job_returns_existing_duplicate(db_session):
    job = schemas.JobCreate(
        title="Software Engineer",
        company="OpenAI",
        location="Remote",
        status="Applied",
        job_board_id="oa-duplicate",
    )

    first = crud.create_job(db_session, job)
    second = crud.create_job(db_session, job)
    all_jobs = crud.get_jobs(db_session)

    assert second.id == first.id
    assert len(all_jobs) == 1


def test_update_job_returns_none_for_missing_job(db_session):
    updated = crud.update_job(
        db_session,
        999,
        schemas.JobUpdate(status="Rejected"),
    )

    assert updated is None


def test_get_jobs_by_filters_respects_sort_order(db_session):
    jobs = [
        schemas.JobCreate(
            title="Backend Engineer",
            company="Google",
            location="San Francisco, CA",
            status="Applied",
            applied_date=date(2025, 9, 25),
            job_board_id="g-1",
        ),
        schemas.JobCreate(
            title="Frontend Engineer",
            company="Google",
            location="Pittsburgh",
            status="Interview",
            applied_date=date(2025, 9, 27),
            job_board_id="g-2",
        ),
    ]

    for job in jobs:
        crud.create_job(db_session, job)

    results = crud.get_jobs_by_filters(
        db_session,
        company="Google",
        sort_by="applied_date",
        sort_desc=False,
    )

    assert [job.title for job in results] == ["Backend Engineer", "Frontend Engineer"]
