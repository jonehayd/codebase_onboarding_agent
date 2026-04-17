from unittest.mock import MagicMock

from app.rag.prompt_builder import build_prompt, _build_context, _build_chunk_header


CHUNK_WITH_NAME = {
    "chunk_type": "function",
    "name": "get_user",
    "content": "def get_user(db, id): return db.query(User).get(id)",
    "file_path": "app/services/user_service.py",
    "start_line": 10,
    "end_line": 12,
    "distance": 0.1,
}

CHUNK_WITHOUT_NAME = {
    "chunk_type": "imports",
    "name": None,
    "content": "import os\nimport sys",
    "file_path": "app/main.py",
    "start_line": 1,
    "end_line": 2,
    "distance": 0.3,
}


# --- build_prompt tests ---

class TestBuildPrompt:
    def test_returns_a_string(self):
        result = build_prompt("what is this?", [CHUNK_WITH_NAME])
        assert isinstance(result, str)

    def test_contains_the_query(self):
        query = "how does authentication work?"
        result = build_prompt(query, [CHUNK_WITH_NAME])
        assert query in result

    def test_contains_system_instructions(self):
        result = build_prompt("query", [CHUNK_WITH_NAME])
        assert "expert software engineer" in result

    def test_contains_chunk_content(self):
        result = build_prompt("query", [CHUNK_WITH_NAME])
        assert CHUNK_WITH_NAME["content"] in result

    def test_contains_no_relevant_snippets_when_chunks_empty(self):
        result = build_prompt("query", [])
        assert "No relevant code snippets" in result

    def test_contains_answer_label(self):
        result = build_prompt("query", [CHUNK_WITH_NAME])
        assert "Answer:" in result

    def test_contains_question_label(self):
        result = build_prompt("query", [CHUNK_WITH_NAME])
        assert "Question:" in result


# --- _build_context tests ---

class TestBuildContext:
    def test_returns_no_snippets_message_for_empty_list(self):
        result = _build_context([])
        assert result == "No relevant code snippets were found in the repository."

    def test_contains_snippet_header(self):
        result = _build_context([CHUNK_WITH_NAME])
        assert "Snippet 1" in result

    def test_numbers_snippets_sequentially(self):
        result = _build_context([CHUNK_WITH_NAME, CHUNK_WITHOUT_NAME])
        assert "Snippet 1" in result
        assert "Snippet 2" in result

    def test_contains_chunk_content(self):
        result = _build_context([CHUNK_WITH_NAME])
        assert CHUNK_WITH_NAME["content"] in result

    def test_contains_file_path(self):
        result = _build_context([CHUNK_WITH_NAME])
        assert CHUNK_WITH_NAME["file_path"] in result

    def test_contains_preamble(self):
        result = _build_context([CHUNK_WITH_NAME])
        assert "Relevant code snippets" in result

    def test_multiple_chunks_all_contents_present(self):
        result = _build_context([CHUNK_WITH_NAME, CHUNK_WITHOUT_NAME])
        assert CHUNK_WITH_NAME["content"] in result
        assert CHUNK_WITHOUT_NAME["content"] in result


# --- _build_chunk_header tests ---

class TestBuildChunkHeader:
    def test_includes_name_when_present(self):
        result = _build_chunk_header(CHUNK_WITH_NAME)
        assert "get_user" in result

    def test_includes_chunk_type_when_name_present(self):
        result = _build_chunk_header(CHUNK_WITH_NAME)
        assert "function" in result

    def test_includes_file_path(self):
        result = _build_chunk_header(CHUNK_WITH_NAME)
        assert "app/services/user_service.py" in result

    def test_includes_start_and_end_lines(self):
        result = _build_chunk_header(CHUNK_WITH_NAME)
        assert "10" in result
        assert "12" in result

    def test_omits_name_when_none(self):
        result = _build_chunk_header(CHUNK_WITHOUT_NAME)
        assert "`None`" not in result

    def test_returns_location_only_when_name_is_none(self):
        result = _build_chunk_header(CHUNK_WITHOUT_NAME)
        assert "app/main.py" in result
        assert "1" in result
        assert "2" in result

    def test_falls_back_to_unknown_file_when_file_path_missing(self):
        chunk = {"chunk_type": "function", "name": "f", "start_line": 1, "end_line": 5}
        result = _build_chunk_header(chunk)
        assert "unknown file" in result
