import pytest
from sqlalchemy import select
from unittest.mock import MagicMock, patch

from app.config import RepoStatus
from app.db.models import Messages, Repositories, Sessions, ShareableLinks, Users
from app.services.sessions import (
    create_session,
    create_share_link,
    delete_session,
    run_ingestion,
)

OWNER = "sessowner"
NAME = "sessrepo"
URL = f"https://github.com/{OWNER}/{NAME}"
OLD_SHA = "abc1234"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    u = Users(github_id="gh_sess_1", username="sess_tester", email="sess@test.com")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def other_user(db):
    u = Users(github_id="gh_sess_2", username="sess_other", email="other@test.com")
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


@pytest.fixture
def session_record(db, user, completed_repo):
    s = Sessions(user_id=user.id, repo_id=completed_repo.id, title="Test Session")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------

class TestCreateSession:
    def test_creates_new_repo_when_not_found(self, db, user):
        session, repo = create_session(user.id, OWNER, NAME, db, title="My Session")
        assert repo.id is not None
        assert repo.status == RepoStatus.PENDING
        assert repo.owner == OWNER
        assert repo.name == NAME

    def test_creates_session_linked_to_repo(self, db, user):
        session, repo = create_session(user.id, OWNER, NAME, db, title="My Session")
        assert session.id is not None
        assert session.repo_id == repo.id
        assert session.user_id == user.id

    def test_sets_session_title(self, db, user):
        session, _ = create_session(user.id, OWNER, NAME, db, title="My Title")
        assert session.title == "My Title"

    def test_title_defaults_to_none(self, db, user):
        session, _ = create_session(user.id, OWNER, NAME, db)
        assert session.title is None

    def test_reuses_existing_repo(self, db, user, completed_repo):
        session, repo = create_session(user.id, OWNER, NAME, db, title="Second Session")
        assert repo.id == completed_repo.id

    def test_reused_repo_retains_status(self, db, user, completed_repo):
        _, repo = create_session(user.id, OWNER, NAME, db)
        assert repo.status == RepoStatus.COMPLETED

    def test_two_users_can_share_same_repo(self, db, user, other_user, completed_repo):
        sess1, repo1 = create_session(user.id, OWNER, NAME, db)
        sess2, repo2 = create_session(other_user.id, OWNER, NAME, db)
        assert repo1.id == repo2.id
        assert sess1.id != sess2.id


# ---------------------------------------------------------------------------
# run_ingestion
# ---------------------------------------------------------------------------

class TestRunIngestion:
    def test_skips_completed_repo(self, db, completed_repo):
        with patch("app.services.sessions.fetch_repo") as mock_fetch:
            run_ingestion(completed_repo.id, OWNER, NAME, db)
            mock_fetch.assert_not_called()

    def test_skips_when_repo_not_found(self, db):
        with patch("app.services.sessions.fetch_repo") as mock_fetch:
            run_ingestion(99999, OWNER, NAME, db)
            mock_fetch.assert_not_called()

    @patch("app.services.sessions.ingest_repo")
    @patch("app.services.sessions.get_latest_commit_hash", return_value="newsha")
    @patch("app.services.sessions.fetch_repo")
    def test_runs_full_ingest_for_pending_repo(self, mock_fetch, mock_hash, mock_ingest, db):
        repo = Repositories(owner=OWNER, name=NAME, url=URL, status=RepoStatus.PENDING)
        db.add(repo)
        db.commit()
        db.refresh(repo)
        mock_fetch.return_value = MagicMock()

        run_ingestion(repo.id, OWNER, NAME, db)

        mock_ingest.assert_called_once()

    @patch("app.services.sessions.ingest_changed_files")
    @patch("app.services.sessions.get_latest_commit_hash", return_value="newsha")
    @patch("app.services.sessions.fetch_repo")
    def test_runs_incremental_ingest_when_commit_hash_differs(self, mock_fetch, mock_hash, mock_ingest, db):
        repo = Repositories(
            owner=OWNER, name=NAME, url=URL, commit_hash=OLD_SHA, status=RepoStatus.PROCESSING
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)
        mock_fetch.return_value = MagicMock()

        run_ingestion(repo.id, OWNER, NAME, db)

        mock_ingest.assert_called_once()

    @patch("app.services.sessions.ingest_repo")
    @patch("app.services.sessions.get_latest_commit_hash", return_value="newsha")
    @patch("app.services.sessions.fetch_repo")
    def test_passes_github_token_to_fetch_repo(self, mock_fetch, mock_hash, mock_ingest, db):
        repo = Repositories(owner=OWNER, name=NAME, url=URL, status=RepoStatus.PENDING)
        db.add(repo)
        db.commit()
        db.refresh(repo)
        mock_fetch.return_value = MagicMock()

        run_ingestion(repo.id, OWNER, NAME, db, github_token="user_gh_token")

        mock_fetch.assert_called_once_with(OWNER, NAME, token="user_gh_token")

    @patch("app.services.sessions.ingest_repo")
    @patch("app.services.sessions.get_latest_commit_hash", return_value="newsha")
    @patch("app.services.sessions.fetch_repo")
    def test_passes_none_token_by_default(self, mock_fetch, mock_hash, mock_ingest, db):
        repo = Repositories(owner=OWNER, name=NAME, url=URL, status=RepoStatus.PENDING)
        db.add(repo)
        db.commit()
        db.refresh(repo)
        mock_fetch.return_value = MagicMock()

        run_ingestion(repo.id, OWNER, NAME, db)

        mock_fetch.assert_called_once_with(OWNER, NAME, token=None)


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------

class TestDeleteSession:
    def test_returns_false_when_session_not_found(self, db, user):
        result = delete_session(99999, user.id, db)
        assert result is False

    def test_returns_false_when_user_does_not_own_session(self, db, other_user, session_record):
        result = delete_session(session_record.id, other_user.id, db)
        assert result is False

    def test_returns_true_on_success(self, db, user, session_record):
        result = delete_session(session_record.id, user.id, db)
        assert result is True

    def test_session_is_removed_from_db(self, db, user, session_record):
        session_id = session_record.id
        delete_session(session_id, user.id, db)
        remaining = db.execute(
            select(Sessions).where(Sessions.id == session_id)
        ).scalar_one_or_none()
        assert remaining is None

    def test_deletes_repo_when_no_other_sessions_reference_it(self, db, user, session_record, completed_repo):
        repo_id = completed_repo.id
        delete_session(session_record.id, user.id, db)
        remaining_repo = db.execute(
            select(Repositories).where(Repositories.id == repo_id)
        ).scalar_one_or_none()
        assert remaining_repo is None

    def test_keeps_repo_when_other_sessions_reference_it(self, db, user, other_user, session_record, completed_repo):
        other_session = Sessions(user_id=other_user.id, repo_id=completed_repo.id)
        db.add(other_session)
        db.commit()

        repo_id = completed_repo.id
        delete_session(session_record.id, user.id, db)

        remaining_repo = db.execute(
            select(Repositories).where(Repositories.id == repo_id)
        ).scalar_one_or_none()
        assert remaining_repo is not None

    def test_deletes_messages_for_session(self, db, user, session_record):
        msg = Messages(session_id=session_record.id, role="user", content="hello")
        db.add(msg)
        db.commit()

        delete_session(session_record.id, user.id, db)

        remaining = db.execute(
            select(Messages).where(Messages.session_id == session_record.id)
        ).all()
        assert remaining == []

    def test_deletes_share_links_for_session(self, db, user, session_record):
        link = ShareableLinks(session_id=session_record.id, created_by=user.id, token="tok123abc")
        db.add(link)
        db.commit()

        delete_session(session_record.id, user.id, db)

        remaining = db.execute(
            select(ShareableLinks).where(ShareableLinks.session_id == session_record.id)
        ).all()
        assert remaining == []


# ---------------------------------------------------------------------------
# create_share_link
# ---------------------------------------------------------------------------

class TestCreateShareLink:
    def test_creates_new_link(self, db, user, session_record):
        link = create_share_link(session_record.id, user.id, db)
        assert link.id is not None
        assert link.session_id == session_record.id
        assert link.created_by == user.id
        assert link.token is not None

    def test_returns_existing_link_on_second_call(self, db, user, session_record):
        link1 = create_share_link(session_record.id, user.id, db)
        link2 = create_share_link(session_record.id, user.id, db)
        assert link1.id == link2.id
        assert link1.token == link2.token

    def test_different_sessions_get_different_tokens(self, db, user, other_user, completed_repo, session_record):
        other_session = Sessions(user_id=other_user.id, repo_id=completed_repo.id)
        db.add(other_session)
        db.commit()
        db.refresh(other_session)

        link1 = create_share_link(session_record.id, user.id, db)
        link2 = create_share_link(other_session.id, other_user.id, db)
        assert link1.token != link2.token
