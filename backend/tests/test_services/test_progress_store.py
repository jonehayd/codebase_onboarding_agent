import time

import pytest

from app.services import progress_store
from app.services.progress_store import IngestionCancelledError


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset module-level state before each test."""
    with progress_store._lock:
        progress_store._progress.clear()
        progress_store._cancel_flags.clear()
    yield
    with progress_store._lock:
        progress_store._progress.clear()
        progress_store._cancel_flags.clear()


# --- init_progress ---

class TestInitProgress:
    def test_creates_entry(self):
        progress_store.init_progress(1)
        assert progress_store.get_progress(1) is not None

    def test_default_stage_is_fetching_files(self):
        progress_store.init_progress(1)
        assert progress_store.get_progress(1)["stage"] == "fetching_files"

    def test_default_percent_is_zero(self):
        progress_store.init_progress(1)
        assert progress_store.get_progress(1)["percent"] == 0

    def test_default_counts_are_zero(self):
        progress_store.init_progress(1)
        p = progress_store.get_progress(1)
        assert p["files_processed"] == 0
        assert p["files_total"] == 0
        assert p["vector_count"] == 0

    def test_clears_existing_cancel_flag(self):
        progress_store.request_cancel(1)
        assert progress_store.is_cancelled(1)
        progress_store.init_progress(1)
        assert not progress_store.is_cancelled(1)

    def test_overwrites_previous_progress(self):
        progress_store.init_progress(1)
        progress_store.update_progress(1, percent=75)
        progress_store.init_progress(1)
        assert progress_store.get_progress(1)["percent"] == 0


# --- update_progress ---

class TestUpdateProgress:
    def test_updates_stage(self):
        progress_store.init_progress(1)
        progress_store.update_progress(1, stage="parsing_code")
        assert progress_store.get_progress(1)["stage"] == "parsing_code"

    def test_updates_multiple_fields(self):
        progress_store.init_progress(1)
        progress_store.update_progress(1, percent=50, files_processed=10, files_total=20)
        p = progress_store.get_progress(1)
        assert p["percent"] == 50
        assert p["files_processed"] == 10
        assert p["files_total"] == 20

    def test_ignores_unknown_repo_id(self):
        # Should not raise
        progress_store.update_progress(999, percent=50)

    def test_partial_update_preserves_other_fields(self):
        progress_store.init_progress(1)
        progress_store.update_progress(1, files_total=15)
        progress_store.update_progress(1, percent=30)
        p = progress_store.get_progress(1)
        assert p["files_total"] == 15
        assert p["percent"] == 30


# --- get_progress ---

class TestGetProgress:
    def test_returns_none_for_unknown_repo(self):
        assert progress_store.get_progress(999) is None

    def test_elapsed_seconds_computed_from_started_at(self):
        progress_store.init_progress(1)
        p = progress_store.get_progress(1)
        assert isinstance(p["elapsed_seconds"], int)
        assert p["elapsed_seconds"] >= 0

    def test_elapsed_seconds_uses_final_elapsed_when_set(self):
        progress_store.init_progress(1)
        with progress_store._lock:
            progress_store._progress[1]["final_elapsed"] = 99
        p = progress_store.get_progress(1)
        assert p["elapsed_seconds"] == 99

    def test_started_at_not_exposed(self):
        progress_store.init_progress(1)
        assert "started_at" not in progress_store.get_progress(1)

    def test_final_elapsed_not_exposed(self):
        progress_store.init_progress(1)
        assert "final_elapsed" not in progress_store.get_progress(1)

    def test_returns_copy_not_reference(self):
        progress_store.init_progress(1)
        p = progress_store.get_progress(1)
        p["percent"] = 99
        assert progress_store.get_progress(1)["percent"] == 0


# --- mark_completed ---

class TestMarkCompleted:
    def test_sets_stage_completed(self):
        progress_store.init_progress(1)
        progress_store.mark_completed(1)
        assert progress_store.get_progress(1)["stage"] == "completed"

    def test_sets_percent_100(self):
        progress_store.init_progress(1)
        progress_store.mark_completed(1)
        assert progress_store.get_progress(1)["percent"] == 100

    def test_freezes_elapsed_seconds(self):
        progress_store.init_progress(1)
        progress_store.mark_completed(1)
        p1 = progress_store.get_progress(1)["elapsed_seconds"]
        time.sleep(0.05)
        p2 = progress_store.get_progress(1)["elapsed_seconds"]
        assert p1 == p2

    def test_ignores_unknown_repo_id(self):
        # Should not raise
        progress_store.mark_completed(999)


# --- mark_failed ---

class TestMarkFailed:
    def test_sets_stage_failed(self):
        progress_store.init_progress(1)
        progress_store.mark_failed(1)
        assert progress_store.get_progress(1)["stage"] == "failed"

    def test_sets_stage_cancelled_when_flag_set(self):
        progress_store.init_progress(1)
        progress_store.mark_failed(1, cancelled=True)
        assert progress_store.get_progress(1)["stage"] == "cancelled"

    def test_discards_cancel_flag(self):
        progress_store.init_progress(1)
        progress_store.request_cancel(1)
        progress_store.mark_failed(1)
        assert not progress_store.is_cancelled(1)

    def test_freezes_elapsed_seconds(self):
        progress_store.init_progress(1)
        progress_store.mark_failed(1)
        p1 = progress_store.get_progress(1)["elapsed_seconds"]
        time.sleep(0.05)
        p2 = progress_store.get_progress(1)["elapsed_seconds"]
        assert p1 == p2

    def test_ignores_unknown_repo_id(self):
        # Should not raise
        progress_store.mark_failed(999)


# --- request_cancel / is_cancelled ---

class TestCancelFlags:
    def test_is_cancelled_false_initially(self):
        assert not progress_store.is_cancelled(1)

    def test_is_cancelled_true_after_request(self):
        progress_store.request_cancel(1)
        assert progress_store.is_cancelled(1)

    def test_init_progress_clears_flag(self):
        progress_store.request_cancel(1)
        progress_store.init_progress(1)
        assert not progress_store.is_cancelled(1)

    def test_mark_failed_clears_flag(self):
        progress_store.request_cancel(1)
        progress_store.init_progress(1)
        progress_store.mark_failed(1)
        assert not progress_store.is_cancelled(1)

    def test_multiple_repos_independent(self):
        progress_store.request_cancel(1)
        assert not progress_store.is_cancelled(2)
