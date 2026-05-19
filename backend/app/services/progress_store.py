import time
import threading
from typing import Optional

from app.config import settings


class IngestionCancelledError(Exception):
    pass


_PROGRESS_TTL = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Redis-backed implementation
# ---------------------------------------------------------------------------

def _make_redis_client():
    import redis
    return redis.from_url(settings.redis_url, decode_responses=True)


if settings.redis_url:
    _client = _make_redis_client()

    def _pk(repo_id: int) -> str:
        return f"ingestion:progress:{repo_id}"

    def _ck(repo_id: int) -> str:
        return f"ingestion:cancel:{repo_id}"

    def init_progress(repo_id: int) -> None:
        _client.hset(_pk(repo_id), mapping={
            "stage": "fetching_files",
            "files_processed": 0,
            "files_total": 0,
            "vector_count": 0,
            "percent": 0,
            "started_at": time.time(),
            "final_elapsed": "",
            "error_message": "",
        })
        _client.expire(_pk(repo_id), _PROGRESS_TTL)
        _client.delete(_ck(repo_id))

    def update_progress(repo_id: int, **kwargs) -> None:
        if _client.exists(_pk(repo_id)):
            _client.hset(_pk(repo_id), mapping={
                k: ("" if v is None else v) for k, v in kwargs.items()
            })

    def get_progress(repo_id: int) -> Optional[dict]:
        data = _client.hgetall(_pk(repo_id))
        if not data:
            return None
        started_at = float(data.get("started_at") or 0)
        final_elapsed = data.get("final_elapsed", "")
        elapsed_seconds = int(float(final_elapsed)) if final_elapsed else int(time.time() - started_at)
        return {
            "stage": data.get("stage", ""),
            "files_processed": int(data.get("files_processed") or 0),
            "files_total": int(data.get("files_total") or 0),
            "vector_count": int(data.get("vector_count") or 0),
            "percent": int(data.get("percent") or 0),
            "elapsed_seconds": elapsed_seconds,
            "error_message": data.get("error_message") or None,
        }

    def mark_completed(repo_id: int) -> None:
        if not _client.exists(_pk(repo_id)):
            return
        started_at = float(_client.hget(_pk(repo_id), "started_at") or 0)
        _client.hset(_pk(repo_id), mapping={
            "stage": "completed",
            "percent": 100,
            "final_elapsed": int(time.time() - started_at),
        })

    def mark_failed(repo_id: int, cancelled: bool = False, error_message: Optional[str] = None) -> None:
        if _client.exists(_pk(repo_id)):
            started_at = float(_client.hget(_pk(repo_id), "started_at") or 0)
            updates: dict = {
                "stage": "cancelled" if cancelled else "failed",
                "final_elapsed": int(time.time() - started_at),
            }
            if error_message is not None:
                updates["error_message"] = error_message
            _client.hset(_pk(repo_id), mapping=updates)
        _client.delete(_ck(repo_id))

    def request_cancel(repo_id: int) -> None:
        _client.set(_ck(repo_id), "1", ex=3600)

    def is_cancelled(repo_id: int) -> bool:
        return bool(_client.exists(_ck(repo_id)))

    def _flush_test_state() -> None:
        keys = (
            list(_client.scan_iter("ingestion:progress:*"))
            + list(_client.scan_iter("ingestion:cancel:*"))
        )
        if keys:
            _client.delete(*keys)


# ---------------------------------------------------------------------------
# In-memory fallback (used when REDIS_URL is not set — e.g. during tests)
# ---------------------------------------------------------------------------

else:
    _lock = threading.Lock()
    _progress: dict[int, dict] = {}
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
                "error_message": None,
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

    def mark_failed(repo_id: int, cancelled: bool = False, error_message: Optional[str] = None) -> None:
        with _lock:
            if repo_id in _progress:
                _progress[repo_id]["stage"] = "cancelled" if cancelled else "failed"
                _progress[repo_id]["final_elapsed"] = int(time.time() - _progress[repo_id]["started_at"])
                if error_message is not None:
                    _progress[repo_id]["error_message"] = error_message
            _cancel_flags.discard(repo_id)

    def request_cancel(repo_id: int) -> None:
        with _lock:
            _cancel_flags.add(repo_id)

    def is_cancelled(repo_id: int) -> bool:
        with _lock:
            return repo_id in _cancel_flags

    def _flush_test_state() -> None:
        with _lock:
            _progress.clear()
            _cancel_flags.clear()
