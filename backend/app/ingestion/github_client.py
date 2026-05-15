from github import Auth, Github
import github
from app.config import settings
from app.ingestion.filter import should_include

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
    
    auth = Auth.Token(token or settings.github_token)
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
        from app.services.progress_store import is_cancelled, IngestionCancelledError
        if is_cancelled(repo_id):
            raise IngestionCancelledError()

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
        return files
    except github.RateLimitExceededException:
        print(f"GitHub API rate limit exceeded while fetching files from {repo.full_name} at path '{path}'")
        raise
    except github.UnknownObjectException:
        print(f"Path '{path}' not found in repository {repo.full_name} or private repository access issue")
        raise
    except Exception as e:
        print(f"Error fetching files from {repo.full_name} at path '{path}': {e}")
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
            print(f"Error fetching {path} from {repo.full_name}: {e}")
    return files