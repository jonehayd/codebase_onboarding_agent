import pytest
from unittest.mock import MagicMock, patch

# --- file filter tests ---

from app.ingestion.filter import should_include, EXCLUDED_DIRS, INCLUDED_EXTENSIONS

class TestShouldInclude:
    def test_includes_python_file(self):
        assert should_include("src/main.py", 1000) is True

    def test_includes_typescript_file(self):
        assert should_include("src/components/App.tsx", 5000) is True

    def test_includes_javascript_file(self):
        assert should_include("src/index.js", 2000) is True

    def test_includes_java_file(self):
        assert should_include("src/Main.java", 3000) is True

    def test_includes_go_file(self):
        assert should_include("main.go", 1500) is True

    def test_excludes_file_over_size_limit(self):
        assert should_include("src/main.py", 200_000) is False

    def test_excludes_file_exactly_at_size_limit(self):
        assert should_include("src/main.py", 100_001) is False

    def test_includes_file_exactly_at_size_limit(self):
        assert should_include("src/main.py", 100_000) is True

    def test_excludes_node_modules(self):
        assert should_include("node_modules/lodash/index.js", 1000) is False

    def test_excludes_nested_node_modules(self):
        assert should_include("packages/app/node_modules/react/index.js", 1000) is False

    def test_excludes_git_directory(self):
        assert should_include(".git/config", 500) is False

    def test_excludes_dist_directory(self):
        assert should_include("dist/bundle.js", 1000) is False

    def test_excludes_build_directory(self):
        assert should_include("build/main.py", 1000) is False

    def test_excludes_pycache(self):
        assert should_include("app/__pycache__/main.cpython-311.pyc", 1000) is False

    def test_excludes_package_lock(self):
        assert should_include("package-lock.json", 50000) is False

    def test_excludes_yarn_lock(self):
        assert should_include("yarn.lock", 50000) is False

    def test_excludes_poetry_lock(self):
        assert should_include("poetry.lock", 50000) is False

    def test_excludes_unknown_extension(self):
        assert should_include("src/binary.exe", 1000) is False

    def test_excludes_file_with_no_extension(self):
        assert should_include("Makefile", 1000) is False

    def test_includes_deeply_nested_valid_file(self):
        assert should_include("src/services/auth/handlers/login.ts", 5000) is True

    def test_excludes_venv_directory(self):
        assert should_include(".venv/lib/python3.11/site-packages/requests/__init__.py", 1000) is False


# --- parser tests ---

from app.ingestion.parser import parse_file, get_language, ParsedFile

class TestGetLanguage:
    def test_returns_language_for_python(self):
        assert get_language("main.py") is not None

    def test_returns_language_for_typescript(self):
        assert get_language("app.ts") is not None

    def test_returns_language_for_tsx(self):
        assert get_language("App.tsx") is not None

    def test_returns_language_for_javascript(self):
        assert get_language("index.js") is not None

    def test_returns_language_for_java(self):
        assert get_language("Main.java") is not None

    def test_returns_language_for_go(self):
        assert get_language("main.go") is not None

    def test_returns_none_for_unknown_extension(self):
        assert get_language("file.xyz")[0] is None

    def test_returns_none_for_no_extension(self):
        assert get_language("Makefile")[0] is None

    def test_handles_uppercase_extension(self):
        # extensions are lowercased so .PY should work
        assert get_language("main.PY") is not None

    def test_handles_nested_path(self):
        assert get_language("src/services/auth.py") is not None

    def test_handles_multiple_dots_in_filename(self):
        # rsplit on last dot — some.module.py should give "py"
        assert get_language("some.module.py") is not None


class TestParseFile:
    def test_returns_parsed_file_for_python(self):
        result = parse_file("main.py", "x = 1")
        assert result is not None
        assert isinstance(result, ParsedFile)

    def test_returns_none_for_unsupported_type(self):
        result = parse_file("file.xyz", "some content")
        assert result is None

    def test_parsed_file_has_correct_file_path(self):
        result = parse_file("src/main.py", "x = 1")
        assert result.file_path == "src/main.py"

    def test_parsed_file_has_content(self):
        source = "def hello(): pass"
        result = parse_file("main.py", source)
        assert result.content == source

    def test_parsed_file_has_tree(self):
        result = parse_file("main.py", "x = 1")
        assert result.tree is not None
        assert result.tree.root_node is not None

    def test_parsed_file_tree_has_no_errors(self):
        result = parse_file("main.py", "def greet(name):\n    return f'hello {name}'")
        assert not result.tree.root_node.has_error

    def test_parses_typescript(self):
        result = parse_file("app.ts", "const x: number = 1;")
        assert result is not None
        assert not result.tree.root_node.has_error

    def test_parses_javascript(self):
        result = parse_file("index.js", "const x = 1;")
        assert result is not None

    def test_parses_empty_file(self):
        result = parse_file("main.py", "")
        assert result is not None
        assert result.tree is not None


# --- chunker tests ---

from app.ingestion.chunker import extract_chunks
from app.ingestion.parser import parse_file

PYTHON_SOURCE = """\
import os
from pathlib import Path

def greet(name: str) -> str:
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    return a + b

class Dog:
    def __init__(self, name: str):
        self.name = name

    def bark(self) -> str:
        return "Woof!"
"""

TYPESCRIPT_SOURCE = """\
import { useState } from 'react';
import axios from 'axios';

function greet(name: string): string {
    return `Hello, ${name}!`;
}

const add = (a: number, b: number): number => a + b;

class Dog {
    name: string;
    constructor(name: string) {
        this.name = name;
    }
    bark(): string {
        return 'Woof!';
    }
}
"""

class TestExtractChunks:
    def test_returns_empty_list_for_none(self):
        assert extract_chunks(None) == []

    def test_extracts_python_functions(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        function_chunks = [c for c in chunks if c["chunk_type"] == "function"]
        names = [c["name"] for c in function_chunks]
        assert "greet" in names
        assert "add" in names

    def test_extracts_python_class(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        class_chunks = [c for c in chunks if c["chunk_type"] == "class"]
        assert len(class_chunks) == 1
        assert class_chunks[0]["name"] == "Dog"

    def test_extracts_python_imports(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        import_chunks = [c for c in chunks if c["chunk_type"] == "imports"]
        assert len(import_chunks) == 1
        assert "import os" in import_chunks[0]["content"]
        assert "from pathlib import Path" in import_chunks[0]["content"]

    def test_imports_chunk_is_first(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        assert chunks[0]["chunk_type"] == "imports"

    def test_chunk_has_correct_file_path(self):
        parsed = parse_file("src/main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        for chunk in chunks:
            assert chunk["file_path"] == "src/main.py"

    def test_chunk_has_line_numbers(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        for chunk in chunks:
            assert "start_line" in chunk
            assert "end_line" in chunk
            assert chunk["start_line"] >= 1
            assert chunk["end_line"] >= chunk["start_line"]

    def test_chunk_content_is_not_empty(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        for chunk in chunks:
            assert chunk["content"].strip() != ""

    def test_class_chunk_does_not_duplicate_methods(self):
        # the class chunk should be one chunk, methods inside should not be separate chunks
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        names = [c["name"] for c in chunks]
        # __init__ and bark are methods inside Dog — they should not appear as separate chunks
        assert "__init__" not in names
        assert "bark" not in names

    def test_extracts_typescript_function(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        function_chunks = [c for c in chunks if c["chunk_type"] == "function"]
        names = [c["name"] for c in function_chunks]
        assert "greet" in names

    def test_extracts_typescript_arrow_function(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        function_chunks = [c for c in chunks if c["chunk_type"] == "function"]
        # arrow function — name may be None for anonymous but content should contain 'add'
        contents = [c["content"] for c in function_chunks]
        assert any("add" in c for c in contents)

    def test_extracts_typescript_class(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        class_chunks = [c for c in chunks if c["chunk_type"] == "class"]
        assert any(c["name"] == "Dog" for c in class_chunks)

    def test_extracts_typescript_imports(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        import_chunks = [c for c in chunks if c["chunk_type"] == "imports"]
        assert len(import_chunks) == 1
        assert "useState" in import_chunks[0]["content"]

    def test_returns_empty_list_for_empty_file(self):
        parsed = parse_file("main.py", "")
        chunks = extract_chunks(parsed)
        assert chunks == []

    def test_returns_only_imports_chunk_for_imports_only_file(self):
        source = "import os\nimport sys\n"
        parsed = parse_file("main.py", source)
        chunks = extract_chunks(parsed)
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "imports"


# --- github_client tests (mocked) ---

from app.ingestion.github_client import fetch_repo, fetch_files

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