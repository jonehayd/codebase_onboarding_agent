import pytest
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker

from app.db.database import Base

TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/onboarding_test"
ADMIN_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/postgres"


@pytest.fixture(scope="session")
def engine():
    admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'onboarding_test'")
        ).fetchone()
        if not exists:
            conn.execute(text("CREATE DATABASE onboarding_test"))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(engine):
    """Wraps each test in an outer transaction + savepoint so that commit()
    calls inside the code under test are rolled back at teardown."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.expire_all()
            sess.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()
