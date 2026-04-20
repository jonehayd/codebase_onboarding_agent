import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select
from sqlalchemy import delete as sql_delete

from app.config import RepoStatus, settings
from app.db.models import CodeChunks, Files, Messages, Repositories, Sessions, ShareableLinks
from app.ingestion.github_client import fetch_repo
from app.services.analyze import (
    get_latest_commit_hash,
    ingest_repo,
    ingest_changed_files,
)


def create_session(
    user_id: int, owner: str, name: str, db: DBSession, title: str | None = None
) -> tuple[Sessions, Repositories]:
    """Find or create a repo record, then create a new session linked to it.

    Returns (session, repo). The repo may already exist (any status) or be freshly
    created with PENDING status — the caller is responsible for triggering ingestion.
    """
    url = f"https://github.com/{owner}/{name}"
    repo = db.execute(
        select(Repositories).where(Repositories.url == url)
    ).scalar_one_or_none()

    if repo is None:
        repo = Repositories(owner=owner, name=name, url=url, status=RepoStatus.PENDING)
        db.add(repo)
        db.commit()
        db.refresh(repo)

    session = Sessions(user_id=user_id, repo_id=repo.id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, repo


def run_ingestion(repo_id: int, owner: str, name: str, db: DBSession, github_token: str | None = None) -> None:
    """Run full or incremental ingestion for an existing repo record.

    Skips if the repo is already COMPLETED and up to date.
    """
    repo = db.get(Repositories, repo_id)
    if not repo or repo.status == RepoStatus.COMPLETED:
        return

    gh_repo = fetch_repo(owner, name, token=github_token)
    latest_hash = get_latest_commit_hash(gh_repo)

    if repo.commit_hash and repo.commit_hash != latest_hash:
        ingest_changed_files(repo_id, owner, name, gh_repo, repo.commit_hash, latest_hash, db)
    else:
        ingest_repo(repo_id, owner, name, db, gh_repo=gh_repo)


def delete_session(session_id: int, user_id: int, db: DBSession) -> bool:
    """Delete a session and cascade to messages and share links.

    If no other sessions reference the same repo, also deletes the repo and its data.
    Returns False if the session was not found or not owned by user_id.
    """
    session = db.execute(
        select(Sessions).where(Sessions.id == session_id, Sessions.user_id == user_id)
    ).scalar_one_or_none()

    if not session:
        return False

    repo_id = session.repo_id

    db.execute(sql_delete(Messages).where(Messages.session_id == session_id))
    db.execute(sql_delete(ShareableLinks).where(ShareableLinks.session_id == session_id))
    db.execute(sql_delete(Sessions).where(Sessions.id == session_id))
    db.commit()

    remaining = db.execute(
        select(Sessions).where(Sessions.repo_id == repo_id)
    ).scalar_one_or_none()

    if not remaining:
        _delete_repo_data(repo_id, db)

    return True


def purge_stale_sessions(db: DBSession) -> int:
    """Delete all sessions inactive for more than 7 days, cascading to messages,
    share links, and orphaned repo data. Returns the number of sessions deleted.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(weeks=1)

    stale_ids = db.execute(
        select(Sessions.id).where(Sessions.last_active_at < cutoff)
    ).scalars().all()

    if not stale_ids:
        return 0

    stale_repo_ids = db.execute(
        select(Sessions.repo_id).where(Sessions.id.in_(stale_ids))
    ).scalars().all()

    db.execute(sql_delete(Messages).where(Messages.session_id.in_(stale_ids)))
    db.execute(sql_delete(ShareableLinks).where(ShareableLinks.session_id.in_(stale_ids)))
    db.execute(sql_delete(Sessions).where(Sessions.id.in_(stale_ids)))
    db.commit()

    for repo_id in set(stale_repo_ids):
        remaining = db.execute(
            select(Sessions).where(Sessions.repo_id == repo_id)
        ).scalar_one_or_none()
        if not remaining:
            _delete_repo_data(repo_id, db)

    return len(stale_ids)


def _delete_repo_data(repo_id: int, db: DBSession) -> None:
    """Delete files, chunks, and repo record for a given repo."""
    file_ids = db.execute(
        select(Files.id).where(Files.repo_id == repo_id)
    ).scalars().all()

    if file_ids:
        db.execute(sql_delete(CodeChunks).where(CodeChunks.file_id.in_(file_ids)))

    db.execute(sql_delete(Files).where(Files.repo_id == repo_id))
    db.execute(sql_delete(Repositories).where(Repositories.id == repo_id))
    db.commit()


def create_share_link(session_id: int, user_id: int, db: DBSession) -> ShareableLinks:
    """Return existing share link or create a new one for the given session."""
    existing = db.execute(
        select(ShareableLinks).where(
            ShareableLinks.session_id == session_id,
            ShareableLinks.created_by == user_id,
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    token = secrets.token_urlsafe(16)
    link = ShareableLinks(session_id=session_id, created_by=user_id, token=token)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
