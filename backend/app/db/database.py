from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

SQLALCHEMY_DATABASE_URL = "sqlite:///./jobs.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine )

Base = declarative_base()


def ensure_sqlite_job_schema(db_engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return

    inspector = inspect(db_engine)
    if "jobs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("jobs")}
    missing_columns: dict[str, str] = {
        "posting_id": "INTEGER",
        "gmail_thread_id": "VARCHAR",
        "ats_source": "VARCHAR",
        "ats_requisition_id": "VARCHAR",
        "ats_application_id": "VARCHAR",
        "ats_candidate_id": "VARCHAR",
    }
    missing_definitions = {
        name: definition
        for name, definition in missing_columns.items()
        if name not in existing_columns
    }

    if missing_definitions:
        with db_engine.begin() as connection:
            for name, definition in missing_definitions.items():
                connection.execute(text(f"ALTER TABLE jobs ADD COLUMN {name} {definition}"))

    desired_indexes = (
        "CREATE INDEX IF NOT EXISTS ix_jobs_posting_id ON jobs (posting_id)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_gmail_thread_id ON jobs (gmail_thread_id)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_source ON jobs (ats_source)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_requisition_id ON jobs (ats_requisition_id)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_application_id ON jobs (ats_application_id)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_candidate_id ON jobs (ats_candidate_id)",
    )
    with db_engine.begin() as connection:
        for statement in desired_indexes:
            connection.execute(text(statement))

    if "gmail_import_sessions" in inspector.get_table_names():
        session_columns = {column["name"] for column in inspector.get_columns("gmail_import_sessions")}
        missing_session_columns: dict[str, str] = {
            "cached_items": "INTEGER NOT NULL DEFAULT 0",
            "cache_hit": "VARCHAR NOT NULL DEFAULT 'false'",
            "preview_payload_json": "TEXT",
            "error_message": "TEXT",
        }
        with db_engine.begin() as connection:
            for name, definition in missing_session_columns.items():
                if name not in session_columns:
                    connection.execute(
                        text(f"ALTER TABLE gmail_import_sessions ADD COLUMN {name} {definition}")
                    )

    if "job_postings" in inspector.get_table_names():
        with db_engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_job_postings_normalized_company ON job_postings (normalized_company)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_job_postings_normalized_title ON job_postings (normalized_title)"
                )
            )


# Dependency
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
