from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import CodeChunks, Files, Repositories, UserRepositories, Users

limiter = Limiter(key_func=get_remote_address)
from app.config import settings

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
    
@router.get("/{repo_id}/files/{file_id}/content")
@limiter.limit("200/hour")
def get_file_content(
    repo_id: int,
    file_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the content of a specific file in a repository.

    Args:
        repo_id (int): The ID of the repository.
        file_id (int): The ID of the file.
        current_user (Users, optional): The authenticated user. Defaults to Depends(get_current_user).
        db (Session, optional): The database session. Defaults to Depends(get_db).

    Raises:
        HTTPException: If the repository is not found.
        HTTPException: If the file is not found.
        HTTPException: If there is an error fetching the file from GitHub.

    Returns:
        dict: The file content and metadata.
    """
    
    access = db.execute(
        select(UserRepositories).where(
            UserRepositories.user_id == current_user.id,
            UserRepositories.repo_id == repo_id,
        )
    ).scalar_one_or_none()

    if not access:
        raise HTTPException(status_code=404, detail="Repository not found")

    file = db.execute(
        select(Files).where(
            Files.id == file_id,
            Files.repo_id == repo_id,
        )
    ).scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    repo = db.get(Repositories, repo_id)

    try:
        from github import Auth, Github
        token = current_user.github_token or settings.github_token
        g = Github(auth=Auth.Token(token))
        gh_repo = g.get_repo(f"{repo.owner}/{repo.name}")
        gh_file = gh_repo.get_contents(file.file_path)
        content = gh_file.decoded_content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch file from GitHub: {e}",
        )

    return {
        "id": file.id,
        "file_path": file.file_path,
        "language": file.language,
        "content": content,
    }