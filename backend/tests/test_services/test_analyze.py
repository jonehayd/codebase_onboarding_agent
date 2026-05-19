import pytest
from sqlalchemy import select
from unittest.mock import MagicMock, patch

from app.config import RepoStatus
from app.db.models import CodeChunks, Files, Repositories, Users
from app.services.analyze import (
    analyze_repo,
    create_repo_record,
    get_changed_file_paths,
    get_latest_commit_hash,
    get_repo_by_url,
    ingest_changed_files,
    ingest_repo,
    update_repo_status,
    _run_pipeline,
)

OWNER = "testowner"
NAME = "testrepo"
URL = f"https://github.com/{OWNER}/{NAME}"
OLD_SHA = "abc1234"
NEW_SHA = "def5678"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    branch = MagicMock()
    branch.commit.sha = latest_sha
    gh_repo = MagicMock()
    gh_repo.default_branch = "main"
    gh_repo.get_branch.return_value = branch
    gh_repo.size = 0  # explicitly set so the size check doesn't reject it
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

    def test_added_and_modified_go_into_ingest_and_delete(self):
        gh_repo = MagicMock()
        added = MagicMock(filename="new.py", status="added")
        modified = MagicMock(filename="changed.py", status="modified")
        gh_repo.compare.return_value = self._make_comparison([added, modified])

        paths_to_ingest, paths_to_delete = get_changed_file_paths(gh_repo, OLD_SHA, NEW_SHA)

        assert paths_to_ingest == {"new.py", "changed.py"}
        assert paths_to_delete == {"new.py", "changed.py"}

    def test_removed_files_go_into_delete_only(self):
        gh_repo = MagicMock()
        deleted = MagicMock(filename="gone.py", status="removed")
        gh_repo.compare.return_value = self._make_comparison([deleted])

        paths_to_ingest, paths_to_delete = get_changed_file_paths(gh_repo, OLD_SHA, NEW_SHA)

        assert paths_to_ingest == set()
        assert paths_to_delete == {"gone.py"}

    def test_renamed_files_handled_correctly(self):
        gh_repo = MagicMock()
        renamed = MagicMock(filename="new_name.py", previous_filename="old_name.py", status="renamed")
        gh_repo.compare.return_value = self._make_comparison([renamed])

        paths_to_ingest, paths_to_delete = get_changed_file_paths(gh_repo, OLD_SHA, NEW_SHA)

        assert paths_to_ingest == {"new_name.py"}
        assert paths_to_delete == {"old_name.py", "new_name.py"}

    def test_returns_empty_sets_when_no_changes(self):
        gh_repo = MagicMock()
        gh_repo.compare.return_value = self._make_comparison([])

        paths_to_ingest, paths_to_delete = get_changed_file_paths(gh_repo, OLD_SHA, NEW_SHA)

        assert paths_to_ingest == set()
        assert paths_to_delete == set()


# ---------------------------------------------------------------------------
# _run_pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    @patch("app.services.analyze.embed_chunks", return_value=[FAKE_VECTOR])
    @patch("app.services.analyze._fetch_and_parse", return_value=(_make_file_dict(), [FAKE_CHUNK]))
    def test_persists_file_and_chunk(self, mock_fp, mock_embed, db, completed_repo):
        _run_pipeline(completed_repo.id, _make_gh_repo(), ["src/main.py"], db)

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

    @patch("app.services.analyze._fetch_and_parse", return_value=None)
    def test_skips_files_that_return_none(self, mock_fp, db, completed_repo):
        _run_pipeline(completed_repo.id, _make_gh_repo(), ["src/main.py"], db)
        result = db.execute(
            select(Files).where(Files.repo_id == completed_repo.id)
        ).all()
        assert result == []

    @patch("app.services.analyze.embed_chunks", return_value=[FAKE_VECTOR])
    @patch(
        "app.services.analyze._fetch_and_parse",
        side_effect=lambda gh, p: (_make_file_dict(p), [FAKE_CHUNK]),
    )
    def test_processes_multiple_files(self, mock_fp, mock_embed, db, completed_repo):
        _run_pipeline(completed_repo.id, _make_gh_repo(), ["a.py", "b.py"], db)
        count = len(db.execute(select(Files).where(Files.repo_id == completed_repo.id)).all())
        assert count == 2


# ---------------------------------------------------------------------------
# ingest_repo
# ---------------------------------------------------------------------------

class TestIngestRepo:
    @patch("app.services.analyze._run_pipeline")
    @patch("app.services.analyze.get_file_tree", return_value=["src/main.py"])
    def test_sets_completed_status_and_commit_hash(self, mock_tree, mock_pipeline, db):
        gh_repo = _make_gh_repo(NEW_SHA)
        repo = create_repo_record(OWNER, NAME, db)

        ingest_repo(repo.id, OWNER, NAME, db, gh_repo=gh_repo)

        db.refresh(repo)
        assert repo.status == RepoStatus.COMPLETED
        assert repo.commit_hash == NEW_SHA

    @patch("app.services.analyze.get_file_tree", return_value=[])
    def test_sets_failed_status_when_no_files(self, mock_tree, db):
        gh_repo = _make_gh_repo()
        repo = create_repo_record(OWNER, NAME, db)

        ingest_repo(repo.id, OWNER, NAME, db, gh_repo=gh_repo)

        db.refresh(repo)
        assert repo.status == RepoStatus.FAILED

    @patch("app.services.analyze._run_pipeline", side_effect=Exception("embed error"))
    @patch("app.services.analyze.get_file_tree", return_value=["src/main.py"])
    def test_sets_failed_status_on_exception(self, mock_tree, mock_pipeline, db):
        gh_repo = _make_gh_repo()
        repo = create_repo_record(OWNER, NAME, db)

        with pytest.raises(RuntimeError, match="Ingestion failed"):
            ingest_repo(repo.id, OWNER, NAME, db, gh_repo=gh_repo)

        db.refresh(repo)
        assert repo.status == RepoStatus.FAILED

    @patch("app.services.analyze._run_pipeline")
    @patch("app.services.analyze.get_file_tree", return_value=["src/main.py"])
    @patch("app.services.analyze.fetch_repo")
    def test_fetches_gh_repo_when_not_provided(self, mock_fetch_repo, mock_tree, mock_pipeline, db):
        mock_fetch_repo.return_value = _make_gh_repo()
        repo = create_repo_record(OWNER, NAME, db)

        ingest_repo(repo.id, OWNER, NAME, db)

        mock_fetch_repo.assert_called_once_with(OWNER, NAME)


# ---------------------------------------------------------------------------
# ingest_changed_files
# ---------------------------------------------------------------------------

class TestIngestChangedFiles:
    @patch("app.services.analyze._run_pipeline")
    @patch("app.services.analyze.get_changed_file_paths", return_value=({"src/main.py"}, set()))
    def test_updates_commit_hash_on_success(self, mock_paths, mock_pipeline, db, completed_repo):
        gh_repo = _make_gh_repo()

        ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        db.refresh(completed_repo)
        assert completed_repo.commit_hash == NEW_SHA
        assert completed_repo.status == RepoStatus.COMPLETED

    @patch("app.services.analyze.get_changed_file_paths", return_value=(set(), set()))
    def test_skips_ingest_when_no_changes(self, mock_paths, db, completed_repo):
        gh_repo = _make_gh_repo()

        ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        db.refresh(completed_repo)
        assert completed_repo.status == RepoStatus.COMPLETED

    @patch("app.services.analyze._run_pipeline", side_effect=Exception("embed error"))
    @patch("app.services.analyze.get_changed_file_paths", return_value=({"src/main.py"}, set()))
    def test_sets_failed_status_on_exception(self, mock_paths, mock_pipeline, db, completed_repo):
        gh_repo = _make_gh_repo()

        with pytest.raises(RuntimeError, match="Incremental ingestion failed"):
            ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        db.refresh(completed_repo)
        assert completed_repo.status == RepoStatus.FAILED

    @patch("app.services.analyze._run_pipeline")
    @patch("app.services.analyze.get_changed_file_paths", return_value=({"src/main.py"}, set()))
    def test_only_processes_changed_paths(self, mock_paths, mock_pipeline, db, completed_repo):
        gh_repo = _make_gh_repo()

        ingest_changed_files(completed_repo.id, OWNER, NAME, gh_repo, OLD_SHA, NEW_SHA, db)

        mock_pipeline.assert_called_once()
        assert set(mock_pipeline.call_args[0][2]) == {"src/main.py"}


# ---------------------------------------------------------------------------
# analyze_repo
# ---------------------------------------------------------------------------

class TestAnalyzeRepo:
    @patch("app.services.analyze.ingest_repo")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=NEW_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_full_ingest_when_repo_not_in_db(self, mock_fetch, mock_hash, mock_ingest, db, user):
        mock_fetch.return_value = _make_gh_repo()

        analyze_repo(user.id, OWNER, NAME, db)

        mock_ingest.assert_called_once()

    @patch("app.services.analyze.ingest_changed_files")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=NEW_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_incremental_ingest_when_commit_hash_stale(
        self, mock_fetch, mock_hash, mock_incremental, db, user, completed_repo
    ):
        mock_fetch.return_value = _make_gh_repo()

        analyze_repo(user.id, OWNER, NAME, db)

        mock_incremental.assert_called_once()

    @patch("app.services.analyze.ingest_repo")
    @patch("app.services.analyze.ingest_changed_files")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=OLD_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_skips_ingest_when_up_to_date(
        self, mock_fetch, mock_hash, mock_incremental, mock_ingest, db, user, completed_repo
    ):
        mock_fetch.return_value = _make_gh_repo(OLD_SHA)

        analyze_repo(user.id, OWNER, NAME, db)

        mock_ingest.assert_not_called()
        mock_incremental.assert_not_called()

    @patch("app.services.analyze.ingest_repo")
    @patch("app.services.analyze.get_latest_commit_hash", return_value=NEW_SHA)
    @patch("app.services.analyze.fetch_repo")
    def test_fetches_from_github_with_owner_and_name(self, mock_fetch, mock_hash, mock_ingest, db, user):
        mock_fetch.return_value = _make_gh_repo()

        analyze_repo(user.id, OWNER, NAME, db)

        mock_fetch.assert_called_once_with(OWNER, NAME)

    @patch("app.services.analyze.fetch_repo", side_effect=ValueError("not found"))
    def test_raises_when_github_repo_not_found(self, mock_fetch, db, user):
        with pytest.raises(ValueError, match="not found"):
            analyze_repo(user.id, OWNER, NAME, db)
