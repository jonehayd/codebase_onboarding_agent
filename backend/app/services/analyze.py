from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import RepoStatus
from app.db.models import CodeChunks, Files, Repositories, UserRepositories
from app.ingestion.chunker import extract_chunks
from app.ingestion.github_client import fetch_files, fetch_files_by_paths, fetch_repo
from app.ingestion.parser import parse_file
from app.rag.embeddings import embed_chunks


def get_repo_by_url(url: str, db: Session) -> Repositories | None:
    """Check if a repo has already been ingested.

    Args:
        url (str): The URL of the repository.
        db (Session): The database session.

    Returns:
        Repositories: The repository object.
    """
    
    stmt = select(Repositories).where(
        Repositories.url == url,
        Repositories.status == RepoStatus.COMPLETED
    )
    
    return db.execute(stmt).scalar_one_or_none()

def create_repo_record(owner: str, name: str, db: Session) -> Repositories:
    """Create a new repository record in the database.

    Args:
        owner (str): The owner of the repository.
        name (str): The name of the repository.
        db (Session): The database session.

    Returns:
        Repositories: The created repository record.
    """
    url = f"https://github.com/{owner}/{name}"
    
    repo = Repositories(
        owner=owner,
        name=name,
        url=url,
        status=RepoStatus.PENDING,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo

def update_repo_status(repo_id: int, status: str, db: Session) -> None:
    """Update the status of a repository.

    Args:
        repo_id (int): The ID of the repository.
        status (str): The new status of the repository.
        db (Session): The database session.
    """
    
    repo = db.get(Repositories, repo_id)
    if repo:
        repo.status = status
        db.commit()
        
def get_latest_commit_hash(gh_repo) -> str:
    """Get the latest commit SHA for the default branch.

    Args:
        gh_repo: The PyGitHub repository object.

    Returns:
        str: The latest commit SHA.
    """
    branch = gh_repo.get_branch(gh_repo.default_branch)
    return branch.commit.sha


def get_changed_file_paths(gh_repo, old_sha: str, new_sha: str) -> set[str]:
    """Get paths of files added or modified between two commits.

    Args:
        gh_repo: The PyGitHub repository object.
        old_sha (str): The older commit SHA.
        new_sha (str): The newer commit SHA.

    Returns:
        set[str]: File paths that were added or modified.
    """
    comparison = gh_repo.compare(old_sha, new_sha)
    return {f.filename for f in comparison.files if f.status in ("added", "modified")}


def add_user_repo(user_id: int, repo_id: int, db: Session) -> None:
    """Add a UserRepositories entry if one does not already exist.

    Args:
        user_id (int): The ID of the user.
        repo_id (int): The ID of the repository.
        db (Session): The database session.
    """
    existing = db.execute(
        select(UserRepositories).where(
            UserRepositories.user_id == user_id,
            UserRepositories.repo_id == repo_id,
        )
    ).scalar_one_or_none()
    if not existing:
        db.add(UserRepositories(user_id=user_id, repo_id=repo_id))
        db.commit()


def _ingest_files(repo_id: int, files: list[dict], db: Session) -> None:
    """Parse, chunk, embed, and persist a list of files for a given repo.

    Args:
        repo_id (int): The ID of the repository.
        files (list[dict]): List of file dicts with keys: path, content, size, language.
        db (Session): The database session.
    """
    for file in files:
        parsed = parse_file(file["path"], file["content"])
        if parsed is None:
            continue

        chunks = extract_chunks(parsed)
        if not chunks:
            continue

        db_file = Files(
            repo_id=repo_id,
            file_path=file["path"],
            language=file["language"],
            size_bytes=file["size"],
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        vectors = embed_chunks(chunks)

        for chunk, vector in zip(chunks, vectors):
            db_chunk = CodeChunks(
                file_id=db_file.id,
                chunk_type=chunk["chunk_type"],
                name=chunk["name"],
                content=chunk["content"],
                start_line=chunk["start_line"],
                end_line=chunk["end_line"],
                embedding=vector,
            )
            db.add(db_chunk)
        db.commit()


def ingest_repo(repo_id: int, owner: str, name: str, db: Session, gh_repo=None) -> None:
    """Full ingestion pipeline:
    1. Fetch all files from GitHub
    2. Parse each file with Tree-sitter
    3. Extract chunks
    4. Save files in db
    5. Embed chunks
    6. Save chunks and embeddings in db
    7. Update repo commit hash and status

    Args:
        repo_id (int): The ID of the repository.
        owner (str): The owner of the repository.
        name (str): The name of the repository.
        db (Session): The database session.
        gh_repo: Optional pre-fetched PyGitHub repository object.
    """
    try:
        update_repo_status(repo_id, RepoStatus.PROCESSING, db)

        if gh_repo is None:
            gh_repo = fetch_repo(owner, name)

        latest_hash = get_latest_commit_hash(gh_repo)
        files = fetch_files(gh_repo)

        if not files:
            update_repo_status(repo_id, RepoStatus.FAILED, db)
            return

        _ingest_files(repo_id, files, db)

        repo = db.get(Repositories, repo_id)
        if repo:
            repo.commit_hash = latest_hash
            repo.status = RepoStatus.COMPLETED
            db.commit()

    except Exception as e:
        update_repo_status(repo_id, RepoStatus.FAILED, db)
        raise RuntimeError(f"Ingestion failed for repo {owner}/{name}: {e}") from e


def ingest_changed_files(
    repo_id: int, owner: str, name: str, gh_repo, old_sha: str, new_sha: str, db: Session
) -> None:
    """Incremental ingestion pipeline: fetch only files changed since old_sha.

    Args:
        repo_id (int): The ID of the repository.
        owner (str): The owner of the repository.
        name (str): The name of the repository.
        gh_repo: The PyGitHub repository object.
        old_sha (str): The commit SHA currently stored in the database.
        new_sha (str): The latest commit SHA from GitHub.
        db (Session): The database session.
    """
    try:
        update_repo_status(repo_id, RepoStatus.PROCESSING, db)

        changed_paths = get_changed_file_paths(gh_repo, old_sha, new_sha)
        if not changed_paths:
            update_repo_status(repo_id, RepoStatus.COMPLETED, db)
            return

        files = fetch_files_by_paths(gh_repo, changed_paths)
        _ingest_files(repo_id, files, db)

        repo = db.get(Repositories, repo_id)
        if repo:
            repo.commit_hash = new_sha
            repo.status = RepoStatus.COMPLETED
            db.commit()

    except Exception as e:
        update_repo_status(repo_id, RepoStatus.FAILED, db)
        raise RuntimeError(f"Incremental ingestion failed for repo {owner}/{name}: {e}") from e


def analyze_repo(user_id: int, owner: str, name: str, db: Session) -> None:
    """Main entry point for repo analysis:
    - If repo is new: run full ingestion
    - If repo exists but commit hash is stale: run incremental ingestion on changed files
    - If repo is up to date: skip ingestion
    - Always ensures a UserRepositories entry exists for the user

    Args:
        user_id (int): The ID of the user requesting the analysis.
        owner (str): The owner of the repository.
        name (str): The name of the repository.
        db (Session): The database session.
    """
    url = f"https://github.com/{owner}/{name}"

    gh_repo = fetch_repo(owner, name)
    latest_hash = get_latest_commit_hash(gh_repo)

    existing = get_repo_by_url(url, db)

    if existing is None:
        print(f"Repository {owner}/{name} not found in database. Starting full ingestion.")
        repo = create_repo_record(owner, name, db)
        ingest_repo(repo.id, owner, name, db, gh_repo=gh_repo)
        repo_id = repo.id
    elif existing.commit_hash != latest_hash:
        print(f"Repository {owner}/{name} has a new commit. Starting incremental ingestion of changed files.")
        ingest_changed_files(existing.id, owner, name, gh_repo, existing.commit_hash, latest_hash, db)
        repo_id = existing.id
    else:
        print(f"Repository {owner}/{name} is up to date. Skipping ingestion.")
        repo_id = existing.id

    add_user_repo(user_id, repo_id, db)



# Test the ingestion pipeline with a real repo
if __name__ == "__main__":
    from app.db.database import init_db, SessionLocal
    from app.db.models import Users

    init_db()
    db = SessionLocal()

    try:
        # Create a test user if one doesn't already exist
        test_user = db.execute(select(Users).where(Users.github_id == "test_user")).scalar_one_or_none()
        if not test_user:
            test_user = Users(github_id="test_user", username="test", email="test@test.com")
            db.add(test_user)
            db.commit()
            db.refresh(test_user)

        analyze_repo(test_user.id, "jonehayd", "discord_bot", db)
        print("Analysis complete")

        from app.db.models import Files, CodeChunks
        from sqlalchemy import select, func

        repo = db.execute(
            select(Repositories).where(Repositories.url == "https://github.com/jonehayd/discord_bot")
        ).scalar_one_or_none()

        if repo:
            file_count = db.execute(select(func.count()).select_from(Files).where(Files.repo_id == repo.id)).scalar()
            chunk_count = db.execute(select(func.count()).select_from(CodeChunks).join(Files).where(Files.repo_id == repo.id)).scalar()
            print(f"Repo status:    {repo.status}")
            print(f"Commit hash:    {repo.commit_hash[:7]}")
            print(f"Files stored:   {file_count}")
            print(f"Chunks stored:  {chunk_count}")

    finally:
        db.close()

            