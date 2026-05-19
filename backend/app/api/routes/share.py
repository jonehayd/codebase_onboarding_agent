import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.schemas import ShareInfoOut
from app.config import settings
from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models import Files, Repositories, Sessions, ShareableLinks
from app.services.chat import get_conversation_history, stream_chat

router = APIRouter(prefix="/share", tags=["share"])


class ShareChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=settings.max_characters_per_question)


@router.get("/{token}", response_model=ShareInfoOut)
def get_shared_repo(
    token: str,
    db: Session = Depends(get_db),
):
    """Get repo metadata for a shareable link. No auth required."""
    link = db.execute(
        select(ShareableLinks).where(ShareableLinks.token == token)
    ).scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked",
        )

    session = db.get(Sessions, link.session_id)
    repo = db.get(Repositories, session.repo_id)

    return {
        "session_id": session.id,
        "repo_id": repo.id,
        "owner": repo.owner,
        "name": repo.name,
        "url": repo.url,
        "status": repo.status,
    }


@router.post("/{token}/chat")
@limiter.limit("20/day")
def shared_chat(
    request: Request,
    token: str,
    body: ShareChatRequest,
    db: Session = Depends(get_db),
):
    """Chat about a repo via a shareable link. No auth required.
    Uses the link creator's context — conversation history is not saved.
    """
    link = db.execute(
        select(ShareableLinks).where(ShareableLinks.token == token)
    ).scalar_one_or_none()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked",
        )

    session = db.get(Sessions, link.session_id)
    repo = db.get(Repositories, session.repo_id)

    if repo.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository is not ready for chat",
        )

    def generate():
        for token_text in stream_chat(
            user_id=link.created_by,
            repo_id=repo.id,
            question=body.question,
            db=db,
            save_messages=False,
        ):
            yield f"data: {json.dumps(token_text)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _resolve_link(token: str, db: Session):
    """Validate token and return (link, session, repo) or raise 404."""
    link = db.execute(
        select(ShareableLinks).where(ShareableLinks.token == token)
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked",
        )
    session = db.get(Sessions, link.session_id)
    repo = db.get(Repositories, session.repo_id)
    return link, session, repo


@router.get("/{token}/history")
def get_shared_history(
    token: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Return the conversation history for a shared session. No auth required."""
    _, session, _ = _resolve_link(token, db)
    return get_conversation_history(session.id, db, limit=limit, offset=offset)


@router.get("/{token}/files")
def list_shared_files(
    token: str,
    db: Session = Depends(get_db),
):
    """List indexed files for a shared session's repo. No auth required."""
    _, session, repo = _resolve_link(token, db)

    files = db.execute(
        select(Files)
        .where(Files.repo_id == repo.id)
        .order_by(Files.file_path.asc())
    ).scalars().all()

    return {
        "session_id": session.id,
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


@router.get("/{token}/files/{file_id}")
@limiter.limit("200/hour")
def get_shared_file_content(
    request: Request,
    token: str,
    file_id: int,
    db: Session = Depends(get_db),
):
    """Fetch file content from GitHub for a shared session. No auth required."""
    _, session, repo = _resolve_link(token, db)

    file = db.execute(
        select(Files).where(Files.id == file_id, Files.repo_id == repo.id)
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not settings.github_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File viewing via share links requires GITHUB_TOKEN to be configured.",
        )

    try:
        from github import Auth, Github

        g = Github(auth=Auth.Token(settings.github_token))
        gh_repo = g.get_repo(f"{repo.owner}/{repo.name}")
        gh_file = gh_repo.get_contents(file.file_path)
        content = gh_file.decoded_content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch file from GitHub: {e}")

    return {
        "id": file.id,
        "file_path": file.file_path,
        "language": file.language,
        "content": content,
    }
