from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import CodeChunks, Files, Repositories, UserRepositories, Users

router = APIRouter(prefix="/repo", tags=["repo"])

@router.get("")
def get_repos(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all repositories the current user has analyzed.

    Args:
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: List of repositories.
    """
    
    stmt = (
        select(Repositories)
        .join(UserRepositories, UserRepositories.repo_id == Repositories.id)
        .where(UserRepositories.user_id == current_user.id)
        .order_by(Repositories.created_at.desc())
    )
    repos = db.execute(stmt).scalars().all()
    
    return {
        "repos": [
            {
                "id": r.id,
                "owner": r.owner,
                "name": r.name,
                "url": r.url,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in repos
        ]
    }
    
@router.get("/{repo_id}")
def get_repo(
    repo_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get metadata for a specific repository.

    Args:
        repo_id (int): The ID of the repository.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: Repository metadata including file and chunk counts.

    Raises:
        HTTPException: If the repo is not found or not accessible.
    """
    access = db.execute(
        select(UserRepositories).where(
            UserRepositories.user_id == current_user.id,
            UserRepositories.repo_id == repo_id,
        )
    ).scalar_one_or_none()

    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    repo = db.get(Repositories, repo_id)

    file_count = db.execute(
        select(func.count()).select_from(Files).where(Files.repo_id == repo_id)
    ).scalar()

    chunk_count = db.execute(
        select(func.count())
        .select_from(CodeChunks)
        .join(Files, Files.id == CodeChunks.file_id)
        .where(Files.repo_id == repo_id)
    ).scalar()

    return {
        "id": repo.id,
        "owner": repo.owner,
        "name": repo.name,
        "url": repo.url,
        "status": repo.status,
        "commit_hash": repo.commit_hash,
        "created_at": repo.created_at,
        "file_count": file_count,
        "chunk_count": chunk_count,
    }
    
@router.get("/{repo_id}/files")
def get_repo_files(
    repo_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the list of indexed files for a repository.

    Args:
        repo_id (int): The ID of the repository.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: List of files in the repository.

    Raises:
        HTTPException: If the repo is not found or not accessible.
    """
    access = db.execute(
        select(UserRepositories).where(
            UserRepositories.user_id == current_user.id,
            UserRepositories.repo_id == repo_id,
        )
    ).scalar_one_or_none()

    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    files = db.execute(
        select(Files)
        .where(Files.repo_id == repo_id)
        .order_by(Files.file_path.asc())
    ).scalars().all()

    return {
        "repo_id": repo_id,
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