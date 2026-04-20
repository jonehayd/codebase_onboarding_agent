import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.api.routes.sessions import router
from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Sessions, Users

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
