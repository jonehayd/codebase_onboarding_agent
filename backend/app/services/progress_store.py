import time
import threading
from typing import Optional


class IngestionCancelledError(Exception):
    pass


_lock = threading.Lock()
_progress: dict[int, dict] = {}  # keyed by repo_id
_cancel_flags: set[int] = set()


def init_progress(repo_id: int) -> None:
    with _lock:
        _progress[repo_id] = {
            "stage": "fetching_files",
            "files_processed": 0,
            "files_total": 0,
            "vector_count": 0,
            "percent": 0,
            "started_at": time.time(),
            "final_elapsed": None,
        }
        _cancel_flags.discard(repo_id)


def update_progress(repo_id: int, **kwargs) -> None:
    with _lock:
        if repo_id in _progress:
            _progress[repo_id].update(kwargs)


def get_progress(repo_id: int) -> Optional[dict]:
    with _lock:
        p = _progress.get(repo_id)
        if p is None:
            return None
        result = dict(p)
        if result["final_elapsed"] is not None:
            result["elapsed_seconds"] = result["final_elapsed"]
        else:
            result["elapsed_seconds"] = int(time.time() - p["started_at"])
        del result["started_at"]
        del result["final_elapsed"]
        return result


def mark_completed(repo_id: int) -> None:
    with _lock:
        if repo_id in _progress:
            _progress[repo_id]["stage"] = "completed"
            _progress[repo_id]["percent"] = 100
            _progress[repo_id]["final_elapsed"] = int(time.time() - _progress[repo_id]["started_at"])


def mark_failed(repo_id: int, cancelled: bool = False) -> None:
    with _lock:
        if repo_id in _progress:
            _progress[repo_id]["stage"] = "cancelled" if cancelled else "failed"
            _progress[repo_id]["final_elapsed"] = int(time.time() - _progress[repo_id]["started_at"])
        _cancel_flags.discard(repo_id)


def request_cancel(repo_id: int) -> None:
    with _lock:
        _cancel_flags.add(repo_id)


def is_cancelled(repo_id: int) -> bool:
    with _lock:
        return repo_id in _cancel_flags
