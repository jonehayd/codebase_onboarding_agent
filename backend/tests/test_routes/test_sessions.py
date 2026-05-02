import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.api.routes.sessions import router
from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Repositories, Sessions, Users
from app.config import settings
from app.services import progress_store

app = FastAPI()
app.include_router(router)


def _make_mock_user():
    user = MagicMock(spec=Users)
    user.id = 1
    user.username = "testuser"
    user.github_token = "gh_token"
    return user


def _make_mock_db():
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.execute.return_value.scalar.return_value = 0
    return db


@pytest.fixture()
def client():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
    yield TestClient(app), mock_db
    app.dependency_overrides.clear()


# --- PATCH /sessions/{session_id} ---

class TestPatchSession:
    def test_returns_200(self, client):
        tc, mock_db = client
        mock_session = MagicMock(spec=Sessions)
        mock_session.id = 1
        mock_session.title = "new title"
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_session
        response = tc.patch("/sessions/1", json={"title": "new title"})
        assert response.status_code == 200

    def test_returns_session_id_and_title(self, client):
        tc, mock_db = client
        mock_session = MagicMock(spec=Sessions)
        mock_session.id = 1
        mock_session.title = "new title"
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_session
        data = tc.patch("/sessions/1", json={"title": "new title"}).json()
        assert data["session_id"] == 1
        assert data["title"] == "new title"

    def test_updates_title_on_model(self, client):
        tc, mock_db = client
        mock_session = MagicMock(spec=Sessions)
        mock_session.id = 1
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_session
        tc.patch("/sessions/1", json={"title": "Updated"})
        assert mock_session.title == "Updated"

    def test_commits_after_update(self, client):
        tc, mock_db = client
        mock_session = MagicMock(spec=Sessions)
        mock_session.id = 1
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_session
        tc.patch("/sessions/1", json={"title": "Updated"})
        mock_db.commit.assert_called_once()

    def test_returns_404_for_unknown_session(self, client):
        tc, mock_db = client
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        response = tc.patch("/sessions/999", json={"title": "title"})
        assert response.status_code == 404

    def test_returns_422_without_title(self, client):
        tc, _ = client
        response = tc.patch("/sessions/1", json={})
        assert response.status_code == 422
        
    def test_returns_422_with_empty_title(self, client):
        tc, _ = client
        response = tc.patch("/sessions/1", json={"title": ""})
        assert response.status_code == 422
        
    def test_returns_422_with_too_long_title(self, client):
        tc, _ = client
        long_title = "A" * (settings.max_characters_per_title + 1)
        response = tc.patch("/sessions/1", json={"title": long_title})
        assert response.status_code == 422


# --- GET /sessions/{session_id}/status ---

def _make_mock_repo(repo_id=10, status="completed", commit_hash="abc123"):
    repo = MagicMock(spec=Repositories)
    repo.id = repo_id
    repo.status = status
    repo.commit_hash = commit_hash
    return repo


def _make_status_db(session, repo, file_count=5, vector_count=20):
    """Return a mock DB whose call pattern matches get_session_status."""
    mock_db = MagicMock()
    # First execute call: _get_session_or_404 -> scalar_one_or_none
    # Second execute call: file_count -> scalar
    # Third execute call:  vector_count -> scalar
    mock_db.execute.return_value.scalar_one_or_none.return_value = session
    scalars = iter([file_count, vector_count])
    mock_db.execute.return_value.scalar.side_effect = lambda: next(scalars)
    mock_db.get.return_value = repo
    return mock_db


class TestGetSessionStatus:
    @pytest.fixture()
    def status_client(self):
        mock_session = MagicMock(spec=Sessions)
        mock_session.id = 1
        mock_session.repo_id = 10
        mock_repo = _make_mock_repo()
        mock_db = _make_status_db(mock_session, mock_repo)

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
        yield TestClient(app), mock_db, mock_session, mock_repo
        app.dependency_overrides.clear()

    def test_returns_200(self, status_client):
        tc, *_ = status_client
        with patch.object(progress_store, "get_progress", return_value=None):
            response = tc.get("/sessions/1/status")
        assert response.status_code == 200

    def test_returns_404_for_unknown_session(self, status_client):
        tc, mock_db, *_ = status_client
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        with patch.object(progress_store, "get_progress", return_value=None):
            response = tc.get("/sessions/999/status")
        assert response.status_code == 404

    def test_response_shape(self, status_client):
        tc, *_ = status_client
        with patch.object(progress_store, "get_progress", return_value=None):
            data = tc.get("/sessions/1/status").json()
        for key in ("session_id", "repo_id", "status", "stage", "percent",
                    "files_total", "file_count", "vector_count"):
            assert key in data

    def test_no_progress_completed_repo(self, status_client):
        tc, mock_db, mock_session, mock_repo = status_client
        mock_repo.status = "completed"
        with patch.object(progress_store, "get_progress", return_value=None):
            data = tc.get("/sessions/1/status").json()
        assert data["stage"] == "completed"
        assert data["percent"] == 100
        assert data["elapsed_seconds"] is None

    def test_no_progress_pending_repo(self, status_client):
        tc, mock_db, mock_session, mock_repo = status_client
        mock_repo.status = "pending"
        with patch.object(progress_store, "get_progress", return_value=None):
            data = tc.get("/sessions/1/status").json()
        assert data["stage"] == "fetching_files"
        assert data["percent"] == 0

    def test_no_progress_processing_repo(self, status_client):
        tc, mock_db, mock_session, mock_repo = status_client
        mock_repo.status = "processing"
        with patch.object(progress_store, "get_progress", return_value=None):
            data = tc.get("/sessions/1/status").json()
        assert data["stage"] == "parsing_code"
        assert data["percent"] == 0

    def test_no_progress_failed_repo(self, status_client):
        tc, mock_db, mock_session, mock_repo = status_client
        mock_repo.status = "failed"
        with patch.object(progress_store, "get_progress", return_value=None):
            data = tc.get("/sessions/1/status").json()
        assert data["stage"] == "failed"

    def test_live_progress_data_used(self, status_client):
        tc, *_ = status_client
        fake_prog = {
            "stage": "generating_embeddings",
            "percent": 65,
            "files_total": 30,
            "elapsed_seconds": 42,
        }
        with patch.object(progress_store, "get_progress", return_value=fake_prog):
            data = tc.get("/sessions/1/status").json()
        assert data["stage"] == "generating_embeddings"
        assert data["percent"] == 65
        assert data["files_total"] == 30
        assert data["elapsed_seconds"] == 42

    def test_file_count_and_vector_count_from_db(self, status_client):
        tc, mock_db, mock_session, mock_repo = status_client
        scalars = iter([7, 33])
        mock_db.execute.return_value.scalar.side_effect = lambda: next(scalars)
        with patch.object(progress_store, "get_progress", return_value=None):
            data = tc.get("/sessions/1/status").json()
        assert data["file_count"] == 7
        assert data["vector_count"] == 33

    def test_commit_hash_in_response(self, status_client):
        tc, mock_db, mock_session, mock_repo = status_client
        mock_repo.commit_hash = "deadbeef"
        with patch.object(progress_store, "get_progress", return_value=None):
            data = tc.get("/sessions/1/status").json()
        assert data["commit_hash"] == "deadbeef"


# --- POST /sessions/{session_id}/cancel ---

class TestCancelIngestion:
    @pytest.fixture()
    def cancel_client(self):
        mock_session = MagicMock(spec=Sessions)
        mock_session.id = 1
        mock_session.repo_id = 10
        mock_repo = _make_mock_repo(status="processing")

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_session
        mock_db.get.return_value = mock_repo

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
        yield TestClient(app), mock_db, mock_session, mock_repo
        app.dependency_overrides.clear()

    def test_returns_200_when_processing(self, cancel_client):
        tc, *_ = cancel_client
        with patch.object(progress_store, "request_cancel") as mock_cancel:
            response = tc.post("/sessions/1/cancel")
        assert response.status_code == 200

    def test_returns_200_when_pending(self, cancel_client):
        tc, mock_db, mock_session, mock_repo = cancel_client
        mock_repo.status = "pending"
        with patch.object(progress_store, "request_cancel"):
            response = tc.post("/sessions/1/cancel")
        assert response.status_code == 200

    def test_calls_request_cancel_with_repo_id(self, cancel_client):
        tc, mock_db, mock_session, mock_repo = cancel_client
        with patch.object(progress_store, "request_cancel") as mock_cancel:
            tc.post("/sessions/1/cancel")
        mock_cancel.assert_called_once_with(mock_repo.id)

    def test_returns_detail_message(self, cancel_client):
        tc, *_ = cancel_client
        with patch.object(progress_store, "request_cancel"):
            data = tc.post("/sessions/1/cancel").json()
        assert "detail" in data

    def test_returns_409_when_completed(self, cancel_client):
        tc, mock_db, mock_session, mock_repo = cancel_client
        mock_repo.status = "completed"
        response = tc.post("/sessions/1/cancel")
        assert response.status_code == 409

    def test_returns_409_when_failed(self, cancel_client):
        tc, mock_db, mock_session, mock_repo = cancel_client
        mock_repo.status = "failed"
        response = tc.post("/sessions/1/cancel")
        assert response.status_code == 409

    def test_returns_404_for_unknown_session(self, cancel_client):
        tc, mock_db, *_ = cancel_client
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        response = tc.post("/sessions/999/cancel")
        assert response.status_code == 404
