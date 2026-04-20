from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy import delete as sql_delete
from slowapi import Limiter
from slowapi.util import get_remote_address
import secrets

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import CodeChunks, Files, Messages, Messages, Repositories, Sessions, Sessions, UserRepositories, Users, ShareableLinks

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
    request: Request,
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
    
@router.delete("/{repo_id}")
def delete_repo(
    repo_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a repository and all associated data for the current user.
    If other users have access to the same repo, only removes the association.
    If the current user is the last one, deletes the repo and all its data.

    Args:
        repo_id (int): The ID of the repository.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: Confirmation message.

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

    # remove this user's association
    db.execute(
        sql_delete(UserRepositories).where(
            UserRepositories.user_id == current_user.id,
            UserRepositories.repo_id == repo_id,
        )
    )
    db.commit()

    # check if any other users still have access
    remaining = db.execute(
        select(UserRepositories).where(UserRepositories.repo_id == repo_id)
    ).scalar_one_or_none()

    # if no other users, delete the repo and all its data
    if not remaining:
        _delete_repo_data(repo_id, db)

    return {"message": "Repository deleted successfully"}

@router.post("/{repo_id}/share")
def create_share_link(
    repo_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a shareable link token for a repository.

    Args:
        repo_id (int): The ID of the repository.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: The shareable token and full URL.

    Raises:
        HTTPException: If the repo is not found or not ready.
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
    if repo.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository must be fully ingested before sharing",
        )

    # return existing share link if one already exists
    existing = db.execute(
        select(ShareableLinks).where(
            ShareableLinks.repo_id == repo_id,
            ShareableLinks.created_by == current_user.id,
        )
    ).scalar_one_or_none()

    if existing:
        return {
            "token": existing.token,
            "url": f"{settings.frontend_url}/share/{existing.token}",
        }

    token = secrets.token_urlsafe(16)
    link = ShareableLinks(
        repo_id=repo_id,
        created_by=current_user.id,
        token=token,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return {
        "token": link.token,
        "url": f"{settings.frontend_url}/share/{link.token}",
    }


@router.delete("/{repo_id}/share")
def delete_share_link(
    repo_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a shareable link for a repository.

    Args:
        repo_id (int): The ID of the repository.
        current_user (Users): The authenticated user.
        db (Session): The database session.

    Returns:
        dict: Confirmation message.
    """
    db.execute(
        sql_delete(ShareableLinks).where(
            ShareableLinks.repo_id == repo_id,
            ShareableLinks.created_by == current_user.id,
        )
    )
    db.commit()
    return {"message": "Share link revoked"}

def _delete_repo_data(repo_id: int, db: Session) -> None:
    """Delete a repo and all associated files, chunks, and embeddings.

    Args:
        repo_id (int): The ID of the repository.
        db (Session): The database session.
    """
    # get all file ids for this repo
    file_ids = db.execute(
        select(Files.id).where(Files.repo_id == repo_id)
    ).scalars().all()

    if file_ids:
        # delete chunks (embeddings are a column on chunks, no separate delete needed)
        db.execute(
            sql_delete(CodeChunks).where(CodeChunks.file_id.in_(file_ids))
        )

    # delete sessions and messages
    session_ids = db.execute(
        select(Sessions.id).where(Sessions.repo_id == repo_id)
    ).scalars().all()

    if session_ids:
        db.execute(
            sql_delete(Messages).where(Messages.session_id.in_(session_ids))
        )
        db.execute(
            sql_delete(Sessions).where(Sessions.repo_id == repo_id)
        )

    # delete files
    db.execute(sql_delete(Files).where(Files.repo_id == repo_id))

    # delete repo
    db.execute(
        sql_delete(Repositories).where(Repositories.id == repo_id)
    )

    db.commit()