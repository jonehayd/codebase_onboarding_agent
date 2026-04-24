from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.schemas import ShareInfoOut
from app.config import settings
from app.db.database import get_db
from app.db.models import Repositories, Sessions, ShareableLinks
from app.services.chat import stream_chat

router = APIRouter(prefix="/share", tags=["share"])
limiter = Limiter(key_func=get_remote_address)


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
        ):
            yield f"data: {token_text}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
