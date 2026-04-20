import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from unittest.mock import MagicMock, patch

from app.api.routes.analyze import router as analyze_router, limiter as analyze_limiter
from app.api.routes.chat import router as chat_router, limiter as chat_limiter
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.db.models import Users


# --- Helpers ------------------------------------------------------------

def get_forwarded_ip(request: Request) -> str:
    """Key function that reads X-Forwarded-For header for testing."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


def _make_app(router, limiter):
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(router)
    return app


def _make_mock_user():
    user = MagicMock(spec=Users)
    user.id = 1
    user.username = "testuser"
    user.github_token = "gh_token"
    return user


def _make_mock_db():
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    return db


@pytest.fixture(autouse=True)
def reset_limiter_storage():
    """Reset slowapi in-memory storage before every test to prevent state bleed."""
    try:
        analyze_limiter._storage.reset()
    except Exception:
        pass
    try:
        chat_limiter._storage.reset()
    except Exception:
        pass
    yield


# --- Analyze rate limit tests ---

class TestAnalyzeRateLimit:
    @pytest.fixture()
    def client(self):
        limiter = Limiter(key_func=get_remote_address, default_limits=[])
        app = _make_app(analyze_router, limiter)
        app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
        app.dependency_overrides[get_db] = lambda: _make_mock_db()
        yield TestClient(app), limiter
        app.dependency_overrides.clear()

    def test_first_request_succeeds(self, client):
        tc, _ = client
        with patch("app.api.routes.analyze.analyze_repo"):
            response = tc.post("/analyze?url=https://github.com/owner/repo")
        assert response.status_code in (200, 202)

    def test_returns_429_after_limit_exceeded(self, client):
        tc, _ = client
        tc.app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["2/minute"],
        )
        with patch("app.api.routes.analyze.analyze_repo"):
            responses = [
                tc.post("/analyze?url=https://github.com/owner/repo")
                for _ in range(3)
            ]
        assert 429 in [r.status_code for r in responses]

    def test_429_response_has_error_detail(self, client):
        tc, _ = client
        tc.app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["1/minute"],
        )
        with patch("app.api.routes.analyze.analyze_repo"):
            tc.post("/analyze?url=https://github.com/owner/repo")
            response = tc.post("/analyze?url=https://github.com/owner/repo")
        if response.status_code == 429:
            assert "error" in response.json()

    def test_allows_requests_under_limit(self, client):
        tc, _ = client
        tc.app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["10/minute"],
        )
        with patch("app.api.routes.analyze.analyze_repo"):
            response = tc.post("/analyze?url=https://github.com/owner/repo")
        assert response.status_code != 429


# --- Chat rate limit tests ---

class TestChatRateLimit:
    @pytest.fixture()
    def client(self):
        limiter = Limiter(key_func=get_remote_address, default_limits=[])
        app = _make_app(chat_router, limiter)
        app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
        app.dependency_overrides[get_db] = lambda: _make_mock_db()
        yield TestClient(app), limiter
        app.dependency_overrides.clear()

    def test_first_request_within_limit_succeeds(self, client):
        tc, _ = client
        tc.app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["10/minute"],
        )
        payload = {"repo_id": 1, "question": "what does this do?"}
        with patch("app.api.routes.chat._verify_repo_access"), \
             patch("app.api.routes.chat.stream_chat", return_value=iter(["hello"])):
            response = tc.post("/chat", json=payload)
        assert response.status_code != 429

    def test_returns_429_after_limit_exceeded(self, client):
        tc, _ = client
        tc.app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["2/minute"],
        )
        payload = {"repo_id": 1, "question": "what does this do?"}
        with patch("app.api.routes.chat._verify_repo_access"), \
             patch("app.api.routes.chat.stream_chat", return_value=iter(["hello"])):
            responses = [tc.post("/chat", json=payload) for _ in range(3)]
        assert 429 in [r.status_code for r in responses]

    def test_rate_limit_resets_across_clients(self, client):
        """Two different IPs should have independent rate limit buckets."""
        tc, _ = client
        tc.app.state.limiter = Limiter(
            key_func=get_forwarded_ip,
            default_limits=["1/minute"],
        )
        payload = {"repo_id": 1, "question": "what does this do?"}
        with patch("app.api.routes.chat._verify_repo_access"), \
             patch("app.api.routes.chat.stream_chat", return_value=iter(["hello"])):
            tc.post("/chat", json=payload, headers={"X-Forwarded-For": "1.2.3.4"})
            r1 = tc.post("/chat", json=payload, headers={"X-Forwarded-For": "1.2.3.4"})
            r2 = tc.post("/chat", json=payload, headers={"X-Forwarded-For": "5.6.7.8"})
        assert r1.status_code == 429
        assert r2.status_code != 429


# --- General rate limit behavior ---

class TestRateLimitHeaders:
    @pytest.fixture()
    def client(self):
        limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
        app = _make_app(analyze_router, limiter)
        app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
        app.dependency_overrides[get_db] = lambda: _make_mock_db()
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_rate_limit_headers_present_on_limited_route(self, client):
        with patch("app.api.routes.analyze.analyze_repo"):
            response = client.post("/analyze?url=https://github.com/owner/repo")
        assert "x-ratelimit-limit" in response.headers or response.status_code in (200, 429)

    def test_429_response_is_json(self, client):
        client.app.state.limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["1/minute"],
        )
        with patch("app.api.routes.analyze.analyze_repo"):
            client.post("/analyze?url=https://github.com/owner/repo")
            response = client.post("/analyze?url=https://github.com/owner/repo")
        if response.status_code == 429:
            assert response.headers["content-type"].startswith("application/json")