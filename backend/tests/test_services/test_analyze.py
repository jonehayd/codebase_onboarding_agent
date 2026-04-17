import pytest
from sqlalchemy import create_engine, select, text, event
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch, call

from app.config import RepoStatus
from app.db.database import Base
from app.db.models import CodeChunks, Files, Repositories, UserRepositories, Users
from app.services.analyze import (
    add_user_repo,
    analyze_repo,
    create_repo_record,
    get_changed_file_paths,
    get_latest_commit_hash,
    get_repo_by_url,
    ingest_changed_files,
    ingest_repo,
    update_repo_status,
    _ingest_files,
)

TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/onboarding_test"
ADMIN_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/postgres"

OWNER = "testowner"
NAME = "testrepo"
URL = f"https://github.com/{OWNER}/{NAME}"
OLD_SHA = "abc1234"
NEW_SHA = "def5678"


# ---------------------------------------------------------------------------
# DB Fixtures
# ---------------------------------------------------------------------------

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
    session.begin_nested()  # SAVEPOINT

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        # After each inner commit (savepoint release), create a new savepoint
        if trans.nested and not trans._parent.nested:
            sess.expire_all()
            sess.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def user(db):
    u = Users(github_id="gh_1", username="tester", email="tester@test.com")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def completed_repo(db):
    repo = Repositories(
        owner=OWNER, name=NAME, url=URL, commit_hash=OLD_SHA, status=RepoStatus.COMPLETED
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gh_repo(latest_sha: str = NEW_SHA):
    """Build a minimal PyGitHub repository mock."""
    branch = MagicMock()
    branch.commit.sha = latest_sha

    gh_repo = MagicMock()
    gh_repo.default_branch = "main"
    gh_repo.get_branch.return_value = branch
    return gh_repo


def _make_file_dict(path="src/main.py", content="def foo(): pass", size=100, language="py"):
    return {"path": path, "content": content, "size": size, "language": language}


FAKE_CHUNK = {
    "chunk_type": "function",
    "name": "foo",
    "content": "def foo(): pass",
    "start_line": 1,
    "end_line": 1,
}

FAKE_VECTOR = [0.1] * 1536


# ---------------------------------------------------------------------------
# get_repo_by_url
# ---------------------------------------------------------------------------

class TestGetRepoByUrl:
    def test_returns_repo_when_completed(self, db, completed_repo):
        result = get_repo_by_url(URL, db)
        assert result is not None
        assert result.id == completed_repo.id

    def test_returns_none_when_not_present(self, db):
        result = get_repo_by_url("https://github.com/nobody/nothing", db)
        assert result is None

    def test_returns_none_when_status_not_completed(self, db):
        repo = Repositories(
            owner=OWNER, name=NAME, url=URL, commit_hash="", status=RepoStatus.PENDING
        )
        db.add(repo)
        db.commit()
        result = get_repo_by_url(URL, db)
        assert result is None


# ---------------------------------------------------------------------------
# create_repo_record
# ---------------------------------------------------------------------------

class TestCreateRepoRecord:
    def test_creates_repo_with_pending_status(self, db):
        repo = create_repo_record(OWNER, NAME, db)
        assert repo.id is not None
        assert repo.status == RepoStatus.PENDING
        assert repo.url == URL
        assert repo.owner == OWNER
        assert repo.name == NAME


# ---------------------------------------------------------------------------
# update_repo_status
# ---------------------------------------------------------------------------

class TestUpdateRepoStatus:
    def test_updates_status(self, db, completed_repo):
        update_repo_status(completed_repo.id, RepoStatus.PROCESSING, db)
        db.refresh(completed_repo)
        assert completed_repo.status == RepoStatus.PROCESSING

    def test_no_error_on_missing_repo(self, db):
        # Should silently do nothing
        update_repo_status(99999, RepoStatus.FAILED, db)


# ---------------------------------------------------------------------------
# get_latest_commit_hash
# ---------------------------------------------------------------------------

class TestGetLatestCommitHash:
    def test_returns_sha(self):
        gh_repo = _make_gh_repo(NEW_SHA)
        result = get_latest_commit_hash(gh_repo)
        assert result == NEW_SHA

    def test_calls_get_branch_with_default_branch(self):
        gh_repo = _make_gh_repo()
        get_latest_commit_hash(gh_repo)
        gh_repo.get_branch.assert_called_once_with("main")


# ---------------------------------------------------------------------------
# get_changed_file_paths
# ---------------------------------------------------------------------------

class TestGetChangedFilePaths:
    def _make_comparison(self, files):
        comparison = MagicMock()
        comparison.files = files
        return comparison

    def test_returns_added_and_modified(self):
        gh_repo = MagicMock()
        added = MagicMock(filename="new.py", status="added")
        modified = MagicMock(filename="changed.py", status="modified")
        deleted = MagicMock(filename="gone.py", status="removed")
        gh_repo.compare.return_value = self._make_comparison([added, modified, deleted])

        result = get_changed_file_paths(gh_repo, OLD_SHA, NEW_SHA)

        assert result == {"new.py", "changed.py"}

    def test_excludes_deleted_files(self):
        gh_repo = MagicMock()
        deleted = MagicMock(filename="gone.py", status="removed")
        gh_repo.compare.return_value = self._make_comparison([deleted])

        result = get_changed_file_paths(gh_repo, OLD_SHA, NEW_SHA)

        assert result == set()

    def test_returns_empty_set_when_no_changes(self):
        gh_repo = MagicMock()
        gh_repo.compare.return_value = self._make_comparison([])

        result = get_changed_file_paths(gh_repo, OLD_SHA, NEW_SHA)

        assert result == set()


# ---------------------------------------------------------------------------
# add_user_repo
# ---------------------------------------------------------------------------

class TestAddUserRepo:
    def test_inserts_entry(self, db, user, completed_repo):
        add_user_repo(user.id, completed_repo.id, db)
        entry = db.execute(
            select(UserRepositories).where(
                UserRepositories.user_id == user.id,
                UserRepositories.repo_id == completed_repo.id,
            )
        ).scalar_one_or_none()
        assert entry is not None

    def test_does_not_duplicate_entry(self, db, user, completed_repo):
        add_user_repo(user.id, completed_repo.id, db)
        add_user_repo(user.id, completed_repo.id, db)  # Second call should be a no-op
        count = db.execute(
            select(UserRepositories).where(
                UserRepositories.user_id == user.id,
                UserRepositories.repo_id == completed_repo.id,
            )
        ).all()
        assert len(count) == 1


# ---------------------------------------------------------------------------
# _ingest_files
# ---------------------------------------------------------------------------

class TestIngestFiles:
    @patch("app.services.analyze.embed_chunks", return_value=[FAKE_VECTOR])
    @patch("app.services.analyze.extract_chunks", return_value=[FAKE_CHUNK])
    @patch("app.services.analyze.parse_file", return_value=MagicMock())
    def test_persists_file_and_chunk(self, mock_parse, mock_chunk, mock_embed, db, completed_repo):
        files = [_make_file_dict()]
        _ingest_files(completed_repo.id, files, db)

        db_file = db.execute(
            select(Files).where(Files.repo_id == completed_repo.id)
        ).scalar_one_or_none()
        assert db_file is not None
        assert db_file.file_path == "src/main.py"

        db_chunk = db.execute(
            select(CodeChunks).where(CodeChunks.file_id == db_file.id)
        ).scalar_one_or_none()
        assert db_chunk is not None
        assert db_chunk.name == "foo"

    @patch("app.services.analyze.parse_file", return_value=None)
    def test_skips_unparseable_files(self, mock_parse, db, completed_repo):
        _ingest_files(completed_repo.id, [_make_file_dict()], db)
        result = db.execute(
            select(Files).where(Files.repo_id == completed_repo.id)
        ).all()
        assert result == []

    @patch("app.services.analyze.embed_chunks", return_value=[])
    @patch("app.services.analyze.extract_chunks", return_value=[])
    @patch("app.services.analyze.parse_file", return_value=MagicMock())
    def test_skips_files_with_no_chunks(self, mock_parse, mock_chunk, mock_embed, db, completed_repo):
        _ingest_files(completed_repo.id, [_make_file_dict()], db)
        result = db.execute(
            select(Files).where(Files.repo_id == completed_repo.id)
        ).all()
        assert result == []

    @patch("app.services.analyze.embed_chunks", return_value=[FAKE_VECTOR])
    @patch("app.services.analyze.extract_chunks", return_value=[FAKE_CHUNK])
    @patch("app.services.analyze.parse_file", return_value=MagicMock())
    def test_processes_multiple_files(self, mock_parse, mock_chunk, mock_embed, db, completed_repo):
        files = [_make_file_dict("a.py"), _make_file_dict("b.py")]
        _ingest_files(completed_repo.id, files, db)
        count = len(db.execute(select(Files).where(Files.repo_id == completed_repo.id)).all())
        assert count == 2


# ---------------------------------------------------------------------------
# ingest_repo
# ---------------------------------------------------------------------------

class TestIngestRepo:
    @patch("app.services.analyze._ingest_files")
    @patch("app.services.analyze.fetch_files", return_value=[_make_file_dict()])
    def test_sets_completed_status_and_commit_hash(self, mock_fetch, mock_ingest, db):
        gh_repo = _make_gh_repo(NEW_SHA)
        repo = create_repo_record(OWNER, NAME, db)

        ingest_repo(repo.id, OWNER, NAME, db, gh_repo=gh_repo)

        db.refresh(repo)
        assert repo.status == RepoStatus.COMPLETED
        assert repo.commit_hash == NEW_SHA

    @patch("app.services.analyze.fetch_files", return_value=[])
    def test_sets_failed_status_when_no_files(self, mock_fetch, db):
        gh_repo = _make_gh_repo()
        repo = create_repo_record(OWNER, NAME, db)

        ingest_repo(repo.id, OWNER, NAME, db, gh_repo=gh_repo)

        db.refresh(repo)
        assert repo.status == RepoStatus.FAILED

    @patch("app.services.analyze._ingest_files", side_effect=Exception("embed error"))
    @patch("app.services.analyze.fetch_files", return_value=[_make_file_dict()])
    def test_sets_failed_status_on_exception(self, mock_fetch, mock_ingest, db):
        gh_repo = _make_gh_repo()
        repo = create_repo_record(OWNER, NAME, db)

        with pytest.raises(RuntimeError, match="Ingestion failed"):
            ingest_repo(repo.id, OWNER, NAME, db, gh_repo=gh_repo)

        db.refresh(repo)
        assert repo.status == RepoStatus.FAILED

    @patch("app.services.analyze._ingest_files")
    @patch("app.services.analyze.fetch_files", return_value=[_make_file_dict()])
    @patch("app.services.analyze.fetch_repo")
    def test_fetches_gh_repo_when_not_provided(self, mock_fetch_repo, mock_fetch_files, mock_ingest, db):
        mock_fetch_repo.return_value = _make_gh_repo()
        repo = create_repo_record(OWNER, NAME, db)

        ingest_repo(repo.id, OWNER, NAME, db)

        mock_fetch_repo.assert_called_once_with(OWNER, NAME)


# ---------------------------------------------------------------------------
# ingest_changed_files
# ---------------------------------------------------------------------------

class TestIngestChangedFiles:
    @patch("app.services.analyze._ingest_files")
    @patch("app.services.analyze.fetch_files_by_paths", return_value=[_make_file_dict()])
    @patch("app.services.analyze.get_changed_file_paths", return_value={"src/main.py"})
    def test_updates_commit_hash_on_success(self, mock_paths, mock_fetch, mock_ingest, db, completed_repo):
        gh_repo = _make_gh_repo()

        ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        db.refresh(completed_repo)
        assert completed_repo.commit_hash == NEW_SHA
        assert completed_repo.status == RepoStatus.COMPLETED

    @patch("app.services.analyze.get_changed_file_paths", return_value=set())
    def test_skips_ingest_when_no_changes(self, mock_paths, db, completed_repo):
        gh_repo = _make_gh_repo()

        ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        db.refresh(completed_repo)
        assert completed_repo.status == RepoStatus.COMPLETED

    @patch("app.services.analyze._ingest_files", side_effect=Exception("embed error"))
    @patch("app.services.analyze.fetch_files_by_paths", return_value=[_make_file_dict()])
    @patch("app.services.analyze.get_changed_file_paths", return_value={"src/main.py"})
    def test_sets_failed_status_on_exception(self, mock_paths, mock_fetch, mock_ingest, db, completed_repo):
        gh_repo = _make_gh_repo()

        with pytest.raises(RuntimeError, match="Incremental ingestion failed"):
            ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        db.refresh(completed_repo)
        assert completed_repo.status == RepoStatus.FAILED

    @patch("app.services.analyze._ingest_files")
    @patch("app.services.analyze.fetch_files_by_paths", return_value=[_make_file_dict()])
    @patch("app.services.analyze.get_changed_file_paths", return_value={"src/main.py"})
    def test_only_fetches_changed_paths(self, mock_paths, mock_fetch, mock_ingest, db, completed_repo):
        gh_repo = _make_gh_repo()

        ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        mock_fetch.assert_called_once_with(gh_repo, {"src/main.py"})


# ---------------------------------------------------------------------------
# analyze_repo
# ---------------------------------------------------------------------------

class TestAnalyzeRepo:
    @patch("app.services.analyze.add_user_repo")
    @patch("app.services.analyze.ingest_repo")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=NEW_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_full_ingest_when_repo_not_in_db(
        self, mock_fetch, mock_hash, mock_ingest, mock_add_user, db, user
    ):
        mock_fetch.return_value = _make_gh_repo()

        analyze_repo(user.id, OWNER, NAME, db)

        mock_ingest.assert_called_once()
        mock_add_user.assert_called_once()

    @patch("app.services.analyze.add_user_repo")
    @patch("app.services.analyze.ingest_changed_files")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=NEW_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_incremental_ingest_when_commit_hash_stale(
        self, mock_fetch, mock_hash, mock_incremental, mock_add_user, db, user, completed_repo
    ):
        # completed_repo has OLD_SHA; latest is NEW_SHA
        mock_fetch.return_value = _make_gh_repo()

        analyze_repo(user.id, OWNER, NAME, db)

        mock_incremental.assert_called_once()
        mock_add_user.assert_called_once()

    @patch("app.services.analyze.add_user_repo")
    @patch("app.services.analyze.ingest_repo")
    @patch("app.services.analyze.ingest_changed_files")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=OLD_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_skips_ingest_when_up_to_date(
        self, mock_fetch, mock_hash, mock_incremental, mock_ingest, mock_add_user, db, user, completed_repo
    ):
        # completed_repo has OLD_SHA; latest is also OLD_SHA
        mock_fetch.return_value = _make_gh_repo(OLD_SHA)

        analyze_repo(user.id, OWNER, NAME, db)

        mock_ingest.assert_not_called()
        mock_incremental.assert_not_called()
        mock_add_user.assert_called_once()

    @patch("app.services.analyze.add_user_repo")
    @patch("app.services.analyze.ingest_repo")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=NEW_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_always_calls_add_user_repo(
        self, mock_fetch, mock_hash, mock_ingest, mock_add_user, db, user
    ):
        mock_fetch.return_value = _make_gh_repo()

        analyze_repo(user.id, OWNER, NAME, db)

        mock_add_user.assert_called_once_with(user.id, mock_ingest.call_args[0][0], db)

    @patch("app.services.analyze.fetch_repo", side_effect=ValueError("not found"))
    def test_raises_when_github_repo_not_found(self, mock_fetch, db, user):
        with pytest.raises(ValueError, match="not found"):
            analyze_repo(user.id, OWNER, NAME, db)
