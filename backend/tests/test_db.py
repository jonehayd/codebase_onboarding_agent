import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Repositories, Users

TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/onboarding_test"
ADMIN_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/postgres"

# --- Fixtures for setting up and tearing down the test database ---

# Pytest fixtures for setting up and tearing down the test database
@pytest.fixture(scope="session")
def engine():
    # Create the test database if it doesn't exist
    admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'onboarding_test'")).fetchone()
        if not exists:
            conn.execute(text("CREATE DATABASE onboarding_test"))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine) # Create tables before tests run
    yield engine # Provide the engine to tests
    Base.metadata.drop_all(bind=engine) # Drop tables after tests complete

# Fixture to provide a database session for each test function
@pytest.fixture(scope="function")
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback() # Rollback any changes made during the test
    session.close()
    
# --- Test cases for database operations ---

def test_create_user(db):
    user = Users(github_id="999", username="testuser", email="pytest@test.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    assert user.github_id == "999"
    assert user.username == "testuser"
    assert user.email == "pytest@test.com"
    
def test_read_user(db):
    user = Users(github_id="998", username="readuser", email="readuser@test.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    assert user.github_id == "998"
    assert user.username == "readuser"
    assert user.email == "readuser@test.com"

def test_create_repo(db):
    repo = Repositories(
        owner="testowner",
        name="testrepo",
        url="https://github.com/testowner/testrepo",
        commit_hash="abc123",
        status="pending",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    assert repo.id is not None
    assert repo.status == "pending"