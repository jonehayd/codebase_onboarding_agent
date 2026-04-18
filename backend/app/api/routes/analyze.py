from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Repositories, Users
from app.services.analyze import analyze_repo

router = APIRouter(prefix="/analyze", tags=["analyze"])

def _parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL into owner and repo name.

    Args:
        url (str): A GitHub repository URL.

    Returns:
        tuple[str, str]: The owner and repo name.

    Raises:
        HTTPException: If the URL is not a valid GitHub repository URL.
    """
    
    try:
        url = url.rstrip("/").replace("https://github.com/", "").replace("http://github.com/", "")
        parts = url.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError
        return parts[0], parts[1]
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                             detail="Invalid GitHub URL. Expected format: https://github.com/{owner}/{repo}")
        
@router.post("")
def analayze(
    url: str,
    background_tasks: BackgroundTasks,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start ingestion for a GitHub repository.
    If the repo is already up to date, skips ingestion.
    Returns immediately with a repo_id the client can use to poll status.

    Args:
        url (str): The GitHub repository URL to analyze.
        background_tasks (BackgroundTasks): FastAPI background task runner.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: The repo_id and initial status.
    """
    
    owner, name = _parse_github_url(url)
    background_tasks.add_task(analyze_repo, owner, name, current_user.id, db)
    return {"message": "Analysis started", "owner": owner, "name": name}

@router.get("/status")
def get_status(
    repo_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current ingestion status of a repository.

    Args:
        repo_id (int): The ID of the repository.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: The repo status and metadata.

    Raises:
        HTTPException: If the repo is not found.
    """
    
    repo = db.get(Repositories, repo_id)
    if not repo:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail="Repository not found")
    return {
        "id": repo.id,
        "owner": repo.owner,
        "name": repo.name,
        "status": repo.status,
        "commit_hash": repo.commit_hash,
        "created_at": repo.created_at,
    }