import json
import re
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import select, func

from app.api.dependencies import get_current_user
from app.api.schemas import (
    CreateSessionOut,
    FileContentOut,
    FreshnessOut,
    HistoryOut,
    ListFilesOut,
    ListSessionsOut,
    PatchSessionOut,
    ReingestOut,
    SearchFilesOut,
    SessionDetail,
    SessionStatusOut,
    ShareLinkOut,
)
from app.config import settings
from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models import CodeChunks, Files, Messages, Repositories, Sessions, Users
from app.services import sessions as session_svc
from app.services import progress_store
from app.services.analyze import get_latest_commit_hash
from app.services.chat import get_conversation_history, stream_chat
from app.ingestion.github_client import fetch_repo

router = APIRouter(prefix="/sessions", tags=["sessions"])


# GitHub username: 1-39 chars, alphanumeric + hyphens, no leading/trailing hyphen
_OWNER_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
# GitHub repo name: 1-100 chars, alphanumeric + hyphens + underscores + dots, no leading dot
_REPO_RE = re.compile(r"^[a-zA-Z0-9_-][a-zA-Z0-9._-]{0,99}$")


def _parse_github_url(url: str) -> tuple[str, str]:
    raw = url.strip()

    # Accept shorthand "owner/repo" with no scheme or host
    if not raw.startswith(("http://", "https://")):
        raw = f"https://github.com/{raw}"

    parsed = urlparse(raw)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid GitHub URL. Expected format: https://github.com/{owner}/{repo}",
        )
    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL must point to github.com",
        )

    parts = parsed.path.strip("/").split("/")
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid GitHub URL. Expected format: https://github.com/{owner}/{repo}",
        )

    owner, repo = parts
    if not _OWNER_RE.match(owner):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid repository owner '{owner}'",
        )
    if not _REPO_RE.match(repo):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid repository name '{repo}'",
        )

    return owner, repo


def _get_session_or_404(session_id: int, user_id: int, db: DBSession) -> Sessions:
    session = db.execute(
        select(Sessions).where(Sessions.id == session_id, Sessions.user_id == user_id)
    ).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=settings.max_characters_per_question)


class PatchSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=settings.max_characters_per_title)


# --- Session CRUD ---

@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateSessionOut)
@limiter.limit("20/day")
def create_session(
    request: Request,
    url: str,
    background_tasks: BackgroundTasks,
    title: str | None = Query(default=None, max_length=settings.max_characters_per_title),
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Create a session for a GitHub repository and trigger ingestion."""
    owner, name = _parse_github_url(url)

    session_count = db.execute(
        select(func.count()).select_from(Sessions).where(Sessions.user_id == current_user.id)
    ).scalar()
    if session_count >= settings.max_sessions_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session limit reached ({settings.max_sessions_per_user} max). Delete an existing session to create a new one.",
        )

    session, repo = session_svc.create_session(current_user.id, owner, name, db, title=title)
    if repo.status != "completed":
        background_tasks.add_task(session_svc.run_ingestion, repo.id, owner, name, db, current_user.github_token)
    return {
        "session_id": session.id,
        "repo_id": repo.id,
        "owner": owner,
        "name": name,
        "status": repo.status,
        "created_at": session.created_at,
    }


@router.get("", response_model=ListSessionsOut)
def list_sessions(
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """List all sessions for the current user with repo metadata."""
    rows = db.execute(
        select(Sessions, Repositories)
        .join(Repositories, Repositories.id == Sessions.repo_id)
        .where(Sessions.user_id == current_user.id)
        .order_by(Sessions.last_active_at.desc())
    ).all()

    return {
        "sessions": [
            {
                "session_id": s.id,
                "title": s.title,
                "repo_id": r.id,
                "owner": r.owner,
                "name": r.name,
                "url": r.url,
                "status": r.status,
                "created_at": s.created_at,
                "last_active_at": s.last_active_at,
            }
            for s, r in rows
        ]
    }


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Get session detail with repo metadata and file/chunk counts."""
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    file_count = db.execute(
        select(func.count()).select_from(Files).where(Files.repo_id == repo.id)
    ).scalar()

    chunk_count = db.execute(
        select(func.count())
        .select_from(CodeChunks)
        .join(Files, Files.id == CodeChunks.file_id)
        .where(Files.repo_id == repo.id)
    ).scalar()

    return {
        "session_id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "last_active_at": session.last_active_at,
        "repo": {
            "id": repo.id,
            "owner": repo.owner,
            "name": repo.name,
            "url": repo.url,
            "status": repo.status,
            "commit_hash": repo.commit_hash,
            "created_at": repo.created_at,
            "file_count": file_count,
            "chunk_count": chunk_count,
        },
    }


@router.patch("/{session_id}", response_model=PatchSessionOut)
def update_session(
    session_id: int,
    body: PatchSessionRequest,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Update a session's title."""
    session = _get_session_or_404(session_id, current_user.id, db)
    session.title = body.title
    db.commit()
    return {"session_id": session.id, "title": session.title}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Delete session, messages, share links, and repo if no other sessions reference it."""
    found = session_svc.delete_session(session_id, current_user.id, db)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


# --- Repo ingestion status ---

@router.get("/{session_id}/status", response_model=SessionStatusOut)
def get_session_status(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Poll repository ingestion status and live progress for this session."""
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    file_count = db.execute(
        select(func.count()).select_from(Files).where(Files.repo_id == repo.id)
    ).scalar()

    vector_count = db.execute(
        select(func.count())
        .select_from(CodeChunks)
        .join(Files, Files.id == CodeChunks.file_id)
        .where(Files.repo_id == repo.id)
    ).scalar()

    prog = progress_store.get_progress(repo.id)

    if prog:
        stage = prog["stage"]
        percent = prog["percent"]
        files_total = prog["files_total"] or file_count
        elapsed_seconds = prog["elapsed_seconds"]
        error_message = prog.get("error_message")
    else:
        _stage_map = {
            "pending": "fetching_files",
            "processing": "parsing_code",
            "completed": "completed",
            "failed": "failed",
        }
        stage = _stage_map.get(repo.status, repo.status)
        percent = 100 if repo.status == "completed" else 0
        files_total = file_count
        elapsed_seconds = None
        error_message = None

    return {
        "session_id": session.id,
        "repo_id": repo.id,
        "status": repo.status,
        "stage": stage,
        "percent": percent,
        "files_total": files_total,
        "file_count": file_count,
        "vector_count": vector_count,
        "elapsed_seconds": elapsed_seconds,
        "commit_hash": repo.commit_hash,
        "error_message": error_message,
    }


@router.post("/{session_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_ingestion(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Request cancellation of an in-progress ingestion for this session."""
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    if repo.status not in ("pending", "processing"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active ingestion to cancel.",
        )

    progress_store.request_cancel(repo.id)
    return {"detail": "Cancellation requested."}


# --- Freshness check ---

@router.get("/{session_id}/freshness", response_model=FreshnessOut)
def get_session_freshness(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Check whether the repository has new commits since the last ingest."""
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    try:
        gh_repo = fetch_repo(repo.owner, repo.name, token=current_user.github_token)
        latest_commit = get_latest_commit_hash(gh_repo)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach GitHub: {e}",
        )

    return {
        "is_stale": repo.commit_hash != latest_commit,
        "stored_commit": repo.commit_hash,
        "latest_commit": latest_commit,
    }


# --- Re-ingestion ---

@router.post("/{session_id}/reingest", status_code=status.HTTP_202_ACCEPTED, response_model=ReingestOut)
def reingest_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Trigger a fresh ingestion of the session's repository.

    Runs incrementally if commits have changed since last ingest, otherwise
    runs a full re-ingest. Returns 409 if ingestion is already in progress.
    """
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    if repo.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingestion is already in progress for this repository.",
        )

    repo.status = "pending"
    db.commit()

    background_tasks.add_task(
        session_svc.run_ingestion,
        repo.id,
        repo.owner,
        repo.name,
        db,
        current_user.github_token,
    )

    return {
        "session_id": session.id,
        "repo_id": repo.id,
        "status": "pending",
    }


# --- Chat ---

@router.post("/{session_id}/chat")
@limiter.limit("30/day")
def chat(
    request: Request,
    session_id: int,
    body: ChatRequest,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Stream a chat response about the session's repository via SSE."""
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    if repo.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository is not ready for chat. Current status: {repo.status}",
        )

    def generate():
        for token in stream_chat(
            user_id=current_user.id,
            repo_id=repo.id,
            question=body.question,
            db=db,
            session_id=session_id,
        ):
            yield f"data: {json.dumps(token)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{session_id}/history", response_model=HistoryOut)
def get_history(
    session_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Get conversation history for a session with pagination."""
    _get_session_or_404(session_id, current_user.id, db)
    return get_conversation_history(session_id, db, limit=limit, offset=offset)


# --- Files ---

@router.get("/{session_id}/files", response_model=ListFilesOut)
def list_files(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """List all indexed files for the session's repository."""
    session = _get_session_or_404(session_id, current_user.id, db)

    files = db.execute(
        select(Files)
        .where(Files.repo_id == session.repo_id)
        .order_by(Files.file_path.asc())
    ).scalars().all()

    return {
        "session_id": session_id,
        "files": [
            {
                "id": f.id,
                "file_path": f.file_path,
                "language": f.language,
                "size_bytes": f.size_bytes,
            }
            for f in files
        ],
    }


@router.get("/{session_id}/files/search", response_model=SearchFilesOut)
def search_files(
    session_id: int,
    q: str = Query(..., min_length=1, max_length=200),
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Search indexed files by path for the session's repository."""
    session = _get_session_or_404(session_id, current_user.id, db)

    files = db.execute(
        select(Files)
        .where(Files.repo_id == session.repo_id, Files.file_path.ilike(f"%{q}%"))
        .order_by(Files.file_path.asc())
    ).scalars().all()

    return {
        "session_id": session_id,
        "query": q,
        "files": [
            {
                "id": f.id,
                "file_path": f.file_path,
                "language": f.language,
                "size_bytes": f.size_bytes,
            }
            for f in files
        ],
    }


@router.get("/{session_id}/files/{file_id}", response_model=FileContentOut)
@limiter.limit("200/hour")
def get_file_content(
    request: Request,
    session_id: int,
    file_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Fetch file content from GitHub for the given indexed file."""
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    file = db.execute(
        select(Files).where(Files.id == file_id, Files.repo_id == session.repo_id)
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    try:
        from github import Auth, Github

        token = current_user.github_token or settings.github_token
        g = Github(auth=Auth.Token(token))
        gh_repo = g.get_repo(f"{repo.owner}/{repo.name}")
        gh_file = gh_repo.get_contents(file.file_path, ref=repo.commit_hash)
        content = gh_file.decoded_content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch file from GitHub: {e}")

    return {
        "id": file.id,
        "file_path": file.file_path,
        "language": file.language,
        "content": content,
    }


# --- Share links ---

@router.post("/{session_id}/share", response_model=ShareLinkOut)
def create_share_link(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Generate (or return existing) shareable link for a session."""
    session = _get_session_or_404(session_id, current_user.id, db)
    repo = db.get(Repositories, session.repo_id)

    if repo.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository must be fully ingested before sharing",
        )

    link = session_svc.create_share_link(session_id, current_user.id, db)
    return {
        "token": link.token,
        "url": f"{settings.frontend_url}/share/{link.token}",
    }


@router.delete("/{session_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def delete_share_link(
    session_id: int,
    current_user: Users = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Revoke the shareable link for a session."""
    from sqlalchemy import delete as sql_delete
    from app.db.models import ShareableLinks

    _get_session_or_404(session_id, current_user.id, db)
    db.execute(
        sql_delete(ShareableLinks).where(
            ShareableLinks.session_id == session_id,
            ShareableLinks.created_by == current_user.id,
        )
    )
    db.commit()
