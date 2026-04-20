from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Repositories, UserRepositories, Users
from app.services.chat import stream_chat, get_conversation_history

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    repo_id: int
    question: str
    
def _verify_repo_access(user_id: int, repo_id: int, db: Session) -> bool:
    """Verify the repo exists, is completed, and belongs to the user.

    Args:
        repo_id (int): The ID of the repository.
        user_id (int): The ID of the user.
        db (Session): The database session.

    Returns:
        Repositories: The repository object.

    Raises:
        HTTPException: If the repo is not found, not completed, or not accessible.
    """
    
    repo = db.get(Repositories, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found or repo is private")
    
    if repo.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository is not ready for chat: Current status: {repo.status}"
        )
        
    access = db.execute(
        select(UserRepositories)
        .where(UserRepositories.user_id == user_id)
        .where(UserRepositories.repo_id == repo_id)
    ).scalar_one_or_none()
    
    if not access:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found or repo is private")
    
    return repo

@router.post("")
def chat(
    request: ChatRequest,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """Stream a chat response about a repository.

    Args:
        request (ChatRequest): The chat request containing repo_id and question.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        StreamingResponse: SSE stream of response tokens.
    """
    
    _verify_repo_access(request.repo_id, current_user.id, db)
    
    def generate():
        for token in stream_chat(
            user_id=current_user.id,
            repo_id=request.repo_id,
            question=request.question,
            db=db
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("history/{repo_id}")
def get_history(
    repo_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[dict]:
    """Get the conversation history for a repository.

    Args:
        repo_id (int): The ID of the repository.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        list[dict]: A list of messages in the conversation history.
    """
    
    _verify_repo_access(repo_id, current_user.id, db)
    
    from app.services.chat import get_or_create_session
    session = get_or_create_session(current_user.id, repo_id, db)
    history = get_conversation_history(session.id, db)
    
    return history