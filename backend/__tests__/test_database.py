from datetime import date

from sqlalchemy import create_engine, inspect, text

from backend.app.crud import crud
from backend.app.db.database import ensure_sqlite_job_schema
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


def test_ensure_sqlite_job_schema_adds_missing_gmail_columns(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy_jobs.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE jobs (
                    id INTEGER NOT NULL PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    company VARCHAR NOT NULL,
                    location VARCHAR NOT NULL,
                    status VARCHAR,
                    applied_date DATE,
                    follow_up_date DATE,
                    job_link VARCHAR,
                    job_description VARCHAR,
                    resume_path VARCHAR,
                    job_board_id VARCHAR,
                    source VARCHAR,
                    notes VARCHAR,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )

    ensure_sqlite_job_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("jobs")}

    assert "gmail_thread_id" in columns
    assert "ats_source" in columns
    assert "ats_requisition_id" in columns
    assert "ats_application_id" in columns
    assert "ats_candidate_id" in columns
