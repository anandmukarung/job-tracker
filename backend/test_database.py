from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .database import Base
from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "uri": True},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in memory
Base.metadata.create_all(bind=engine)

# Dependency override for FastAPI
def override_get_db():
    print("USING IN MEMORY DB")
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
