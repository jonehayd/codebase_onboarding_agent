from github import Auth, Github
import github
import logging
from app.config import settings
from app.ingestion.filter import should_include

logger = logging.getLogger(__name__)

# Fetch a requested repository using the GitHub API
def fetch_repo(owner: str, name: str, token: str = None):
    """Fetch a repository from GitHub using the provided owner and name.

    Args:
        owner (str): The owner of the repository.
        name (str): The name of the repository.
        token (str, optional): The GitHub token to use for authentication. Defaults to None.
    Returns:
        github.Repository.Repository: The fetched repository object, or None if an error occurred.
    """    
    
    resolved_token = token or settings.github_token
    if not resolved_token:
        raise ValueError("No GitHub token available. Provide a user token or set GITHUB_TOKEN.")
    auth = Auth.Token(resolved_token)
    g = Github(auth=auth)
    try:
        repo = g.get_repo(f"{owner}/{name}")
        return repo
    except github.UnknownObjectException:
        raise ValueError(f"Repository {owner}/{name} not found or is private")
    except Exception as e:
        raise RuntimeError(f"Error fetching repository {owner}/{name}: {e}") from e
    
# Recursively fetch files from the repository, filtering by size and type
def fetch_files(
    repo: "github.Repository.Repository",
    path: str = "",
    _state: dict | None = None,
    repo_id: int | None = None,
):
    """Recursively fetch files from a GitHub repository, filtering by size and type.

    Args:
        repo (github.Repository.Repository): The repository object.
        path (str, optional): The path within the repository to start fetching from. Defaults to "".
        _state (dict, optional): Internal mutable state for tracking file count across recursion.
        repo_id (int, optional): If provided, cancellation is checked via progress_store each directory.

    Returns:
        list: A list of dictionaries containing the file path, content, size, and language.
    """
    if _state is None:
        _state = {"count": 0}

    # Honour cancel requests between directories
    if repo_id is not None:
        from app.services.progress_store import is_cancelled, update_progress, IngestionCancelledError
        if is_cancelled(repo_id):
            raise IngestionCancelledError()
    else:
        update_progress = None

    if _state["count"] >= settings.max_files_per_repo:
        return []

    try:
        contents = repo.get_contents(path)
        files = []
        for item in contents:
            if _state["count"] >= settings.max_files_per_repo:
                break
            if item.type == "dir":
                files.extend(fetch_files(repo, item.path, _state, repo_id))
            else:
                if should_include(item.path, item.size):
                    raw = item.decoded_content  # file contents as bytes
                    text = raw.decode("utf-8", errors="ignore")
                    files.append({
                        "path": item.path,
                        "content": text,
                        "size": item.size,
                        "language": item.path.rsplit(".", 1)[-1] if "." in item.path else "unknown"
                    })
                    _state["count"] += 1
                    if update_progress is not None:
                        update_progress(repo_id, files_processed=_state["count"])
        return files
    except github.RateLimitExceededException:
        logger.warning("GitHub API rate limit exceeded fetching files from %s at path '%s'", repo.full_name, path)
        raise
    except github.UnknownObjectException:
        logger.warning("Path '%s' not found in %s or private repository access issue", path, repo.full_name)
        raise
    except Exception as e:
        logger.error("Error fetching files from %s at path '%s': %s", repo.full_name, path, e)
        return []

def fetch_files_by_paths(repo: "github.Repository.Repository", paths: set[str]) -> list[dict]:
    """Fetch specific files from a GitHub repository by their paths.

    Args:
        repo (github.Repository.Repository): The repository object.
        paths (set[str]): Set of file paths to fetch.

    Returns:
        list: A list of dictionaries containing the file path, content, size, and language.
    """
    files = []
    for path in paths:
        try:
            item = repo.get_contents(path)
            if should_include(item.path, item.size):
                text = item.decoded_content.decode("utf-8", errors="ignore")
                files.append({
                    "path": item.path,
                    "content": text,
                    "size": item.size,
                    "language": item.path.rsplit(".", 1)[-1] if "." in item.path else "unknown",
                })
        except github.UnknownObjectException:
            pass  # File was deleted in the diff; skip it
        except Exception as e:
            logger.warning("Error fetching %s from %s: %s", path, repo.full_name, e)
    return files


_CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go",
    ".rs", ".cs", ".rb", ".swift", ".cpp", ".c", ".h",
    ".sql", ".sh",
}
_DOC_EXTENSIONS = {".md", ".mdx", ".txt"}


def _path_priority(path: str) -> int:
    """Return sort key: 0 = source code, 1 = config/data, 2 = documentation.

    Applied before the max_files cap so code is never crowded out by docs.
    """
    ext = ("." + path.rsplit(".", 1)[-1].lower()) if "." in path else ""
    if ext in _CODE_EXTENSIONS:
        return 0
    if ext in _DOC_EXTENSIONS:
        return 2
    return 1


def get_file_tree(gh_repo, commit_sha: str) -> list[str]:
    """Return ingestable file paths via the git tree API (single API call).

    Much faster than recursive get_contents() for large repos.
    Falls back to an empty list on error; caller should treat that as fatal.
    """
    try:
        git_commit = gh_repo.get_git_commit(commit_sha)
        tree = gh_repo.get_git_tree(git_commit.tree.sha, recursive=True)

        # Collect every passing path before applying the cap so we can sort
        # by priority first.  Without this, alphabetical tree order meant that
        # docs/ would fill the cap before source code dirs were reached.
        paths = [
            item.path
            for item in tree.tree
            if item.type == "blob" and should_include(item.path, item.size or 0)
        ]

        if tree.truncated:
            logger.warning(
                "Git tree truncated for %s at %d files (GitHub limit); "
                "some files may be missing",
                gh_repo.full_name, len(paths),
            )

        paths.sort(key=_path_priority)

        if len(paths) > settings.max_files_per_repo:
            logger.warning(
                "%s has %d ingestable files; capping at %d (source code prioritised over docs)",
                gh_repo.full_name, len(paths), settings.max_files_per_repo,
            )
            paths = paths[: settings.max_files_per_repo]

        return paths
    except Exception as e:
        logger.error("Failed to fetch git tree for %s: %s", gh_repo.full_name, e)
        return []


def fetch_file_content(gh_repo, path: str) -> dict | None:
    """Fetch and decode content for a single file. Returns None on any error."""
    try:
        item = gh_repo.get_contents(path)
        text = item.decoded_content.decode("utf-8", errors="ignore")
        return {
            "path": path,
            "content": text,
            "size": item.size,
            "language": path.rsplit(".", 1)[-1] if "." in path else "unknown",
        }
    except Exception as e:
        logger.warning("Failed to fetch %s from %s: %s", path, gh_repo.full_name, e)
        return None