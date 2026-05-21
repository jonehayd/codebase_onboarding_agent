import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from sqlalchemy import delete as sql_delete

from app.config import RepoStatus, settings
from app.db.models import CodeChunks, Files, Repositories
from app.ingestion.chunker import extract_chunks
from app.ingestion.github_client import fetch_repo, get_file_tree, fetch_file_content
from app.ingestion.parser import parse_file
from app.rag.embeddings import embed_chunks
from app.services import progress_store
from app.services.progress_store import IngestionCancelledError

logger = logging.getLogger(__name__)


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


def get_changed_file_paths(gh_repo, old_sha: str, new_sha: str) -> tuple[set[str], set[str]]:
    """Get paths of files changed between two commits.

    Args:
        gh_repo: The PyGitHub repository object.
        old_sha (str): The older commit SHA.
        new_sha (str): The newer commit SHA.

    Returns:
        tuple[set[str], set[str]]: (paths_to_ingest, paths_to_delete)
    """
    comparison = gh_repo.compare(old_sha, new_sha)
    paths_to_ingest: set[str] = set()
    paths_to_delete: set[str] = set()
    for f in comparison.files:
        if f.status in ("added", "modified"):
            paths_to_ingest.add(f.filename)
            paths_to_delete.add(f.filename)
        elif f.status == "removed":
            paths_to_delete.add(f.filename)
        elif f.status == "renamed":
            paths_to_ingest.add(f.filename)
            paths_to_delete.add(f.previous_filename)
            paths_to_delete.add(f.filename)
    return paths_to_ingest, paths_to_delete


_PLAIN_TEXT_CHUNK_LINES = 80


def _plain_text_chunks(file: dict) -> list[dict]:
    """Split a plain-text / unsupported file into fixed-size line chunks.

    Used as a fallback for file types without a tree-sitter parser (e.g. Markdown).
    """
    lines = file["content"].split("\n")
    chunks = []
    for i in range(0, len(lines), _PLAIN_TEXT_CHUNK_LINES):
        slice_ = lines[i : i + _PLAIN_TEXT_CHUNK_LINES]
        content = "\n".join(slice_).strip()
        if content:
            chunks.append({
                "file_path": file["path"],
                "chunk_type": "text",
                "name": None,
                "content": content,
                "start_line": i + 1,
                "end_line": i + len(slice_),
            })
    return chunks


def _fetch_and_parse(gh_repo, path: str) -> tuple[dict, list] | None:
    """Fetch a file from GitHub and parse it into chunks. Runs in a worker thread."""
    file = fetch_file_content(gh_repo, path)
    if file is None:
        return None
    parsed = parse_file(file["path"], file["content"])
    chunks = extract_chunks(parsed) if parsed is not None else _plain_text_chunks(file)
    return (file, chunks) if chunks else None


_FETCH_WORKERS = 4
_EMBED_BATCH_SIZE = 100
_SENTINEL = object()


async def _embed_and_persist_batch(pending: list[tuple[int, dict]], db: Session) -> int:
    """Embed a cross-file batch of chunks and bulk-insert into code_chunks. Returns vector count."""
    chunks = [c for _, c in pending]
    vectors = await asyncio.to_thread(embed_chunks, chunks)
    db.execute(
        insert(CodeChunks),
        [
            {
                "file_id": file_id,
                "chunk_type": chunk["chunk_type"],
                "name": chunk["name"],
                "content": chunk["content"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "embedding": vector,
            }
            for (file_id, _), chunk, vector in zip(pending, chunks, vectors)
        ],
    )
    return len(vectors)


async def _run_pipeline_async(repo_id: int, gh_repo, paths: list[str], db: Session) -> None:
    total = len(paths)
    files_done = 0
    vector_count = 0

    progress_store.update_progress(
        repo_id,
        stage="processing",
        files_total=total,
        files_processed=0,
        percent=0,
    )

    queue: asyncio.Queue = asyncio.Queue(maxsize=20)

    async def producer() -> None:
        sem = asyncio.Semaphore(_FETCH_WORKERS)

        async def fetch_one(path: str) -> None:
            async with sem:
                result = await asyncio.to_thread(_fetch_and_parse, gh_repo, path)
            await queue.put(result)

        await asyncio.gather(*[fetch_one(p) for p in paths])
        await queue.put(_SENTINEL)

    async def consumer() -> None:
        nonlocal files_done, vector_count
        pending: list[tuple[int, dict]] = []

        while True:
            if progress_store.is_cancelled(repo_id):
                raise IngestionCancelledError()

            try:
                item = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue  # re-check cancellation flag while producer is still running

            if item is _SENTINEL:
                break

            files_done += 1
            if item is not None:
                file, chunks = item
                if chunks:
                    db_file = Files(
                        repo_id=repo_id,
                        file_path=file["path"],
                        language=file["language"],
                        size_bytes=file["size"],
                    )
                    db.add(db_file)
                    db.flush()

                    for chunk in chunks:
                        pending.append((db_file.id, chunk))

                    if len(pending) >= _EMBED_BATCH_SIZE:
                        if progress_store.is_cancelled(repo_id):
                            raise IngestionCancelledError()
                        count = await _embed_and_persist_batch(pending, db)
                        db.commit()
                        db.expunge_all()
                        vector_count += count
                        pending = []

            progress_store.update_progress(
                repo_id,
                files_processed=files_done,
                percent=int(files_done / max(total, 1) * 100),
                vector_count=vector_count,
            )

        if pending:
            if progress_store.is_cancelled(repo_id):
                raise IngestionCancelledError()
            count = await _embed_and_persist_batch(pending, db)
            db.commit()
            db.expunge_all()
            vector_count += count

        db.commit()

    await asyncio.gather(producer(), consumer())


def _run_pipeline(repo_id: int, gh_repo, paths: list[str], db: Session) -> None:
    """Pipelined ingestion: concurrent fetching with cross-file batched embedding."""
    asyncio.run(_run_pipeline_async(repo_id, gh_repo, paths, db))


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
        logger.info("Starting full ingestion for %s/%s (repo_id=%d)", owner, name, repo_id)
        progress_store.init_progress(repo_id)
        update_repo_status(repo_id, RepoStatus.PROCESSING, db)

        progress_store.update_progress(repo_id, stage="fetching_files", percent=0)

        if gh_repo is None:
            gh_repo = fetch_repo(owner, name)

        # Reject repositories that are clearly too large to process in reasonable time.
        # gh_repo.size is reported by GitHub in KB.
        if gh_repo.size > settings.max_repo_size_kb:
            msg = (
                f"Repository is too large to ingest ({gh_repo.size // 1024} MB). "
                f"Maximum allowed size is {settings.max_repo_size_kb // 1024} MB."
            )
            logger.warning("Rejecting %s/%s: %s", owner, name, msg)
            progress_store.mark_failed(repo_id, error_message=msg)
            repo = db.get(Repositories, repo_id)
            if repo:
                repo.status = RepoStatus.FAILED
                db.commit()
            return

        latest_hash = get_latest_commit_hash(gh_repo)

        paths, was_capped = get_file_tree(gh_repo, latest_hash)

        if was_capped:
            progress_store.update_progress(repo_id, files_truncated=1)

        if not paths:
            logger.warning("No files fetched for %s/%s; marking as failed", owner, name)
            progress_store.mark_failed(repo_id)
            update_repo_status(repo_id, RepoStatus.FAILED, db)
            return

        logger.info("Ingesting %d file(s) for %s/%s", len(paths), owner, name)
        _run_pipeline(repo_id, gh_repo, paths, db)

        repo = db.get(Repositories, repo_id)
        if repo:
            repo.commit_hash = latest_hash
            repo.status = RepoStatus.COMPLETED
            db.commit()

        progress_store.mark_completed(repo_id)
        logger.info("Ingestion complete for %s/%s at %s", owner, name, latest_hash[:7])

    except IngestionCancelledError:
        progress_store.mark_failed(repo_id, cancelled=True)
        update_repo_status(repo_id, RepoStatus.FAILED, db)
        logger.info("Ingestion cancelled for %s/%s", owner, name)

    except Exception as e:
        progress_store.mark_failed(repo_id)
        update_repo_status(repo_id, RepoStatus.FAILED, db)
        logger.exception("Ingestion failed for %s/%s", owner, name)
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
        logger.info(
            "Starting incremental ingestion for %s/%s (repo_id=%d, %s -> %s)",
            owner, name, repo_id, old_sha[:7], new_sha[:7],
        )
        progress_store.init_progress(repo_id)
        update_repo_status(repo_id, RepoStatus.PROCESSING, db)

        progress_store.update_progress(repo_id, stage="fetching_files", percent=0)

        paths_to_ingest, paths_to_delete = get_changed_file_paths(gh_repo, old_sha, new_sha)
        if not paths_to_ingest and not paths_to_delete:
            logger.info("No changed files for %s/%s; already up to date", owner, name)
            update_repo_status(repo_id, RepoStatus.COMPLETED, db)
            progress_store.mark_completed(repo_id)
            return

        # Delete stale Files (and their CodeChunks via cascade) for all affected paths.
        if paths_to_delete:
            stale_file_ids = db.execute(
                select(Files.id).where(
                    Files.repo_id == repo_id,
                    Files.file_path.in_(paths_to_delete),
                )
            ).scalars().all()
            if stale_file_ids:
                db.execute(
                    sql_delete(CodeChunks).where(CodeChunks.file_id.in_(stale_file_ids))
                )
                db.execute(
                    sql_delete(Files).where(Files.id.in_(stale_file_ids))
                )
                db.commit()

        if not paths_to_ingest:
            repo = db.get(Repositories, repo_id)
            if repo:
                repo.commit_hash = new_sha
                repo.status = RepoStatus.COMPLETED
                db.commit()
            progress_store.mark_completed(repo_id)
            logger.info("Incremental ingestion complete for %s/%s at %s (deletions only)", owner, name, new_sha[:7])
            return

        logger.info("Re-ingesting %d changed file(s) for %s/%s", len(paths_to_ingest), owner, name)
        _run_pipeline(repo_id, gh_repo, list(paths_to_ingest), db)

        repo = db.get(Repositories, repo_id)
        if repo:
            repo.commit_hash = new_sha
            repo.status = RepoStatus.COMPLETED
            db.commit()

        progress_store.mark_completed(repo_id)
        logger.info("Incremental ingestion complete for %s/%s at %s", owner, name, new_sha[:7])

    except IngestionCancelledError:
        progress_store.mark_failed(repo_id, cancelled=True)
        update_repo_status(repo_id, RepoStatus.FAILED, db)
        logger.info("Ingestion cancelled for %s/%s", owner, name)

    except Exception as e:
        progress_store.mark_failed(repo_id)
        update_repo_status(repo_id, RepoStatus.FAILED, db)
        logger.exception("Incremental ingestion failed for %s/%s", owner, name)
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
        logger.info("Repository %s/%s not found; starting full ingestion", owner, name)
        repo = create_repo_record(owner, name, db)
        ingest_repo(repo.id, owner, name, db, gh_repo=gh_repo)
    elif existing.commit_hash != latest_hash:
        logger.info("Repository %s/%s has new commits; starting incremental ingestion", owner, name)
        ingest_changed_files(existing.id, owner, name, gh_repo, existing.commit_hash, latest_hash, db)
    else:
        logger.info("Repository %s/%s is up to date; skipping ingestion", owner, name)

      
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
