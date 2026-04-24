from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router
from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Users
from app.utility.auth import _token_blocklist

# Build a minimal app with just the auth router for testing
app = FastAPI()
app.include_router(router)


def _make_db():
    """Return a mock db session wired up as a FastAPI dependency override."""
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    return mock_db


@pytest.fixture()
def client():
    mock_db = _make_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app, follow_redirects=False), mock_db
    app.dependency_overrides.clear()


# --- Helpers ---

def _mock_get_side_effects(profile: dict, emails: list[dict]):
    """Build the two sequential httpx.get side-effects used in the callback."""
    profile_response = MagicMock()
    profile_response.status_code = 200
    profile_response.json.return_value = profile

    email_response = MagicMock()
    email_response.status_code = 200
    email_response.json.return_value = emails

    return [profile_response, email_response]


DEFAULT_PROFILE = {"id": 42, "login": "jonehayd"}
DEFAULT_EMAILS = [{"email": "j@example.com", "primary": True, "verified": True}]


# --- GET /auth/github ---

class TestGithubLogin:
    def test_redirects_to_github(self, client):
        tc, _ = client
        response = tc.get("/auth/github")
        assert response.status_code in (302, 307)

    def test_redirect_url_contains_github_auth_host(self, client):
        tc, _ = client
        response = tc.get("/auth/github")
        assert "github.com/login/oauth/authorize" in response.headers["location"]

    def test_redirect_url_contains_client_id(self, client):
        tc, _ = client
        from app.config import settings
        response = tc.get("/auth/github")
        assert settings.github_client_id in response.headers["location"]

    def test_redirect_url_does_not_include_repo_scope_by_default(self, client):
        tc, _ = client
        response = tc.get("/auth/github")
        location = response.headers["location"]
        # basic flow includes read:user but NOT the bare "repo" scope token
        assert "read" in location
        assert "scope=repo" not in location
        # "repo" only appears as part of "read:user" URL-encoded, not as standalone scope
        assert "scope=read%3Auser%20user%3Aemail" in location or "scope=read:user" in location

    def test_redirect_url_requests_repo_scope_when_private_true(self, client):
        tc, _ = client
        response = tc.get("/auth/github?private=true")
        assert "repo" in response.headers["location"]

    def test_redirect_url_state_is_basic_by_default(self, client):
        tc, _ = client
        response = tc.get("/auth/github")
        assert "state=basic" in response.headers["location"]

    def test_redirect_url_state_is_repo_when_private_true(self, client):
        tc, _ = client
        response = tc.get("/auth/github?private=true")
        assert "state=repo" in response.headers["location"]


# --- GET /auth/github/callback — happy paths ---

class TestGithubCallbackSuccess:
    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_returns_200(self, mock_token, mock_get, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        response = tc.get("/auth/github/callback?code=abc")
        assert response.status_code == 200

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_response_contains_access_token(self, mock_token, mock_get, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        data = tc.get("/auth/github/callback?code=abc").json()
        assert data["access_token"] == "jwt.tok"

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_response_token_type_is_bearer(self, mock_token, mock_get, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        data = tc.get("/auth/github/callback?code=abc").json()
        assert data["token_type"] == "bearer"

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_response_contains_user_info(self, mock_token, mock_get, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        data = tc.get("/auth/github/callback?code=abc").json()
        assert "user" in data
        assert "id" in data["user"]
        assert "username" in data["user"]
        assert "email" in data["user"]

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_creates_new_user_when_not_found(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        tc.get("/auth/github/callback?code=abc")
        mock_db.add.assert_called_once()

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_updates_existing_user_without_add(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        existing_user = MagicMock()
        existing_user.id = 1
        existing_user.username = "jonehayd"
        existing_user.email = "j@example.com"
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        tc.get("/auth/github/callback?code=abc")
        mock_db.add.assert_not_called()

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_updates_github_token_on_existing_user(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        existing_user = MagicMock()
        existing_user.id = 1
        existing_user.username = "jonehayd"
        existing_user.email = "j@example.com"
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
        mock_post.return_value.json.return_value = {"access_token": "new_gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        tc.get("/auth/github/callback?code=abc")
        assert existing_user.github_token == "new_gh_tok"

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_null_email_does_not_update_existing_user_email(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        existing_user = MagicMock()
        existing_user.id = 1
        existing_user.email = "original@example.com"
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        # email endpoint returns no primary verified email
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, [])
        mock_token.return_value = "jwt.tok"
        tc.get("/auth/github/callback?code=abc")
        assert existing_user.email == "original@example.com"

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_commits_and_refreshes_db(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        tc.get("/auth/github/callback?code=abc")
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_has_repo_access_false_without_state(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        data = tc.get("/auth/github/callback?code=abc").json()
        assert data["user"]["has_repo_access"] is False

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_has_repo_access_false_with_basic_state(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        data = tc.get("/auth/github/callback?code=abc&state=basic").json()
        assert data["user"]["has_repo_access"] is False

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_has_repo_access_true_with_repo_state(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        data = tc.get("/auth/github/callback?code=abc&state=repo").json()
        assert data["user"]["has_repo_access"] is True

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    @patch("app.api.routes.auth.create_token")
    def test_has_repo_access_updated_on_existing_user(self, mock_token, mock_get, mock_post, client):
        tc, mock_db = client
        existing_user = MagicMock()
        existing_user.id = 1
        existing_user.username = "jonehayd"
        existing_user.email = "j@example.com"
        existing_user.has_repo_access = False
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        mock_get.side_effect = _mock_get_side_effects(DEFAULT_PROFILE, DEFAULT_EMAILS)
        mock_token.return_value = "jwt.tok"
        tc.get("/auth/github/callback?code=abc&state=repo")
        assert existing_user.has_repo_access is True


# --- GET /auth/github/callback — error paths ---

class TestGithubCallbackErrors:
    @patch("app.api.routes.auth.httpx.post")
    def test_returns_400_on_github_oauth_error(self, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }
        response = tc.get("/auth/github/callback?code=bad")
        assert response.status_code == 400

    @patch("app.api.routes.auth.httpx.post")
    def test_error_detail_contains_github_message(self, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }
        data = tc.get("/auth/github/callback?code=bad").json()
        assert "incorrect or expired" in data["detail"]

    @patch("app.api.routes.auth.httpx.post")
    @patch("app.api.routes.auth.httpx.get")
    def test_returns_502_when_github_profile_fetch_fails(self, mock_get, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {"access_token": "gh_tok"}
        profile_response = MagicMock()
        profile_response.status_code = 401
        mock_get.return_value = profile_response
        response = tc.get("/auth/github/callback?code=abc")
        assert response.status_code == 502

    @patch("app.api.routes.auth.httpx.post")
    def test_returns_400_when_error_description_missing(self, mock_post, client):
        tc, _ = client
        mock_post.return_value.json.return_value = {"error": "some_error"}
        response = tc.get("/auth/github/callback?code=bad")
        assert response.status_code == 400
        assert "some_error" in response.json()["detail"]


# --- GET /auth/me ---

def _make_mock_user():
    user = MagicMock(spec=Users)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.has_repo_access = False
    user.created_at = "2026-01-01T00:00:00"
    return user


@pytest.fixture()
def authed_client():
    mock_db = _make_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
    yield TestClient(app), mock_db
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_blocklist():
    _token_blocklist.clear()
    yield
    _token_blocklist.clear()


class TestGetMe:
    def test_returns_200(self, authed_client):
        tc, _ = authed_client
        response = tc.get("/auth/me")
        assert response.status_code == 200

    def test_returns_user_id(self, authed_client):
        tc, _ = authed_client
        data = tc.get("/auth/me").json()
        assert data["id"] == 1

    def test_returns_username(self, authed_client):
        tc, _ = authed_client
        data = tc.get("/auth/me").json()
        assert data["username"] == "testuser"

    def test_returns_email(self, authed_client):
        tc, _ = authed_client
        data = tc.get("/auth/me").json()
        assert data["email"] == "test@example.com"

    def test_returns_has_repo_access(self, authed_client):
        tc, _ = authed_client
        data = tc.get("/auth/me").json()
        assert "has_repo_access" in data

    def test_returns_created_at(self, authed_client):
        tc, _ = authed_client
        data = tc.get("/auth/me").json()
        assert "created_at" in data

    def test_returns_401_without_token(self, authed_client):
        tc, _ = authed_client
        tc.app.dependency_overrides.pop(get_current_user)
        response = tc.get("/auth/me")
        assert response.status_code in (401, 403)


# --- POST /auth/logout ---

class TestLogout:
    def test_returns_204(self, authed_client):
        tc, _ = authed_client
        response = tc.post("/auth/logout", headers={"Authorization": "Bearer sometoken"})
        assert response.status_code == 204

    def test_adds_token_to_blocklist(self, authed_client):
        tc, _ = authed_client
        tc.post("/auth/logout", headers={"Authorization": "Bearer mytoken"})
        assert "mytoken" in _token_blocklist

    def test_returns_401_without_token(self, authed_client):
        tc, _ = authed_client
        tc.app.dependency_overrides.pop(get_current_user)
        response = tc.post("/auth/logout")
        assert response.status_code in (401, 403)
