from app.ingestion.github_client import fetch_repo, fetch_files
import pytest
from unittest.mock import MagicMock, patch

class TestFetchRepo:
    @patch("app.ingestion.github_client.Github")
    def test_returns_repo_on_success(self, mock_github_class):
        mock_repo = MagicMock()
        mock_github_class.return_value.get_repo.return_value = mock_repo
        result = fetch_repo("jonehayd", "discord_bot")
        assert result == mock_repo

    @patch("app.ingestion.github_client.Github")
    def test_calls_get_repo_with_correct_path(self, mock_github_class):
        mock_github_class.return_value.get_repo.return_value = MagicMock()
        fetch_repo("jonehayd", "discord_bot")
        mock_github_class.return_value.get_repo.assert_called_once_with("jonehayd/discord_bot")

    @patch("app.ingestion.github_client.Github")
    def test_raises_on_unknown_repo(self, mock_github_class):
        import github
        mock_github_class.return_value.get_repo.side_effect = github.UnknownObjectException(404, "Not Found")
        with pytest.raises(ValueError, match="not found or is private"):
            fetch_repo("nobody", "nonexistent")

    @patch("app.ingestion.github_client.Github")
    def test_raises_on_generic_error(self, mock_github_class):
        mock_github_class.return_value.get_repo.side_effect = Exception("network error")
        with pytest.raises(RuntimeError):
            fetch_repo("jonehayd", "discord_bot")
            
class TestFetchFiles:
    def _make_file_item(self, path, content, size=1000):
        item = MagicMock()
        item.type = "file"
        item.path = path
        item.size = size
        item.decoded_content = content.encode("utf-8")
        return item

    def _make_dir_item(self, path):
        item = MagicMock()
        item.type = "dir"
        item.path = path
        return item

    def test_returns_list_of_files(self):
        mock_repo = MagicMock()
        py_file = self._make_file_item("src/main.py", "def hello(): pass")
        mock_repo.get_contents.return_value = [py_file]
        result = fetch_files(mock_repo)
        assert len(result) == 1

    def test_returned_file_has_path(self):
        mock_repo = MagicMock()
        py_file = self._make_file_item("src/main.py", "x = 1")
        mock_repo.get_contents.return_value = [py_file]
        result = fetch_files(mock_repo)
        assert result[0]["path"] == "src/main.py"

    def test_returned_file_has_content(self):
        mock_repo = MagicMock()
        py_file = self._make_file_item("src/main.py", "x = 1")
        mock_repo.get_contents.return_value = [py_file]
        result = fetch_files(mock_repo)
        assert result[0]["content"] == "x = 1"

    def test_excludes_unsupported_file_types(self):
        mock_repo = MagicMock()
        exe_file = self._make_file_item("bin/app.exe", "binary")
        mock_repo.get_contents.return_value = [exe_file]
        result = fetch_files(mock_repo)
        assert result == []

    def test_excludes_files_over_size_limit(self):
        mock_repo = MagicMock()
        large_file = self._make_file_item("src/main.py", "x = 1", size=200_000)
        mock_repo.get_contents.return_value = [large_file]
        result = fetch_files(mock_repo)
        assert result == []

    def test_recurses_into_directories(self):
        mock_repo = MagicMock()
        dir_item = self._make_dir_item("src")
        py_file = self._make_file_item("src/main.py", "x = 1")

        def get_contents_side_effect(path=""):
            if path == "":
                return [dir_item]
            if path == "src":
                return [py_file]
            return []

        mock_repo.get_contents.side_effect = get_contents_side_effect
        result = fetch_files(mock_repo)
        assert len(result) == 1
        assert result[0]["path"] == "src/main.py"

    def test_returns_empty_list_on_error(self):
        mock_repo = MagicMock()
        mock_repo.get_contents.side_effect = Exception("API error")
        result = fetch_files(mock_repo)
        assert result == []

    def test_handles_multiple_files(self):
        mock_repo = MagicMock()
        files = [
            self._make_file_item("main.py", "x = 1"),
            self._make_file_item("app.ts", "const x = 1;"),
            self._make_file_item("Main.java", "class Main {}"),
        ]
        mock_repo.get_contents.return_value = files
        result = fetch_files(mock_repo)
        assert len(result) == 3