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
        "CREATE INDEX IF NOT EXISTS ix_jobs_gmail_thread_id ON jobs (gmail_thread_id)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_source ON jobs (ats_source)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_requisition_id ON jobs (ats_requisition_id)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_application_id ON jobs (ats_application_id)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_ats_candidate_id ON jobs (ats_candidate_id)",
    )
    with db_engine.begin() as connection:
        for statement in desired_indexes:
            connection.execute(text(statement))


# Dependency
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
