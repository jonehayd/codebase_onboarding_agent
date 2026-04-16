import pytest
from unittest.mock import MagicMock, patch

from app.rag.embeddings import build_embed_text, embed_chunks, embed_query


# --- build_embed_text tests ---

class TestBuildEmbedText:
    def test_includes_chunk_type_and_name(self):
        chunk = {"chunk_type": "function", "name": "greet", "content": "def greet(): pass"}
        result = build_embed_text(chunk)
        assert "function greet" in result

    def test_includes_content(self):
        chunk = {"chunk_type": "function", "name": "greet", "content": "def greet(): pass"}
        result = build_embed_text(chunk)
        assert "def greet(): pass" in result

    def test_name_and_content_separated_by_newline(self):
        chunk = {"chunk_type": "function", "name": "greet", "content": "def greet(): pass"}
        result = build_embed_text(chunk)
        assert result == "function greet\ndef greet(): pass"

    def test_omits_name_line_when_name_is_none(self):
        chunk = {"chunk_type": "imports", "name": None, "content": "import os"}
        result = build_embed_text(chunk)
        assert result == "import os"

    def test_omits_name_line_when_name_missing(self):
        chunk = {"chunk_type": "imports", "content": "import os"}
        result = build_embed_text(chunk)
        assert result == "import os"

    def test_returns_empty_string_for_empty_chunk(self):
        result = build_embed_text({})
        assert result == ""

    def test_returns_empty_string_when_content_missing(self):
        chunk = {"chunk_type": "function", "name": "greet"}
        result = build_embed_text(chunk)
        assert result == "function greet"

    def test_class_chunk_type_in_output(self):
        chunk = {"chunk_type": "class", "name": "Dog", "content": "class Dog: pass"}
        result = build_embed_text(chunk)
        assert result.startswith("class Dog")


# --- embed_chunks tests ---

class TestEmbedChunks:
    def _make_mock_response(self, embeddings: list[list[float]]):
        response = MagicMock()
        response.data = [MagicMock(embedding=e) for e in embeddings]
        return response

    def test_returns_empty_list_for_empty_input(self):
        result = embed_chunks([])
        assert result == []

    @patch("app.rag.embeddings.client")
    def test_returns_one_embedding_per_chunk(self, mock_client):
        chunks = [
            {"chunk_type": "function", "name": "greet", "content": "def greet(): pass"},
            {"chunk_type": "function", "name": "add", "content": "def add(a, b): return a + b"},
        ]
        mock_client.embeddings.create.return_value = self._make_mock_response(
            [[0.1] * 1536, [0.2] * 1536]
        )
        result = embed_chunks(chunks)
        assert len(result) == 2

    @patch("app.rag.embeddings.client")
    def test_returns_correct_embedding_values(self, mock_client):
        chunks = [{"chunk_type": "function", "name": "f", "content": "def f(): pass"}]
        expected = [0.5] * 1536
        mock_client.embeddings.create.return_value = self._make_mock_response([expected])
        result = embed_chunks(chunks)
        assert result[0] == expected

    @patch("app.rag.embeddings.client")
    def test_calls_api_with_correct_model(self, mock_client):
        from app.config import settings
        chunks = [{"chunk_type": "function", "name": "f", "content": "def f(): pass"}]
        mock_client.embeddings.create.return_value = self._make_mock_response([[0.1] * 1536])
        embed_chunks(chunks)
        call_kwargs = mock_client.embeddings.create.call_args
        assert call_kwargs.kwargs["model"] == settings.embedding_model

    @patch("app.rag.embeddings.client")
    def test_calls_api_once_for_all_chunks(self, mock_client):
        chunks = [
            {"chunk_type": "function", "name": "a", "content": "def a(): pass"},
            {"chunk_type": "function", "name": "b", "content": "def b(): pass"},
            {"chunk_type": "function", "name": "c", "content": "def c(): pass"},
        ]
        mock_client.embeddings.create.return_value = self._make_mock_response(
            [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        )
        embed_chunks(chunks)
        mock_client.embeddings.create.assert_called_once()

    @patch("app.rag.embeddings.client")
    def test_input_texts_built_from_chunks(self, mock_client):
        chunks = [{"chunk_type": "function", "name": "greet", "content": "def greet(): pass"}]
        mock_client.embeddings.create.return_value = self._make_mock_response([[0.1] * 1536])
        embed_chunks(chunks)
        call_kwargs = mock_client.embeddings.create.call_args
        assert call_kwargs.kwargs["input"] == ["function greet\ndef greet(): pass"]


# --- embed_query tests ---

class TestEmbedQuery:
    def _make_mock_response(self, embedding: list[float]):
        response = MagicMock()
        response.data = [MagicMock(embedding=embedding)]
        return response

    @patch("app.rag.embeddings.client")
    def test_returns_list_of_floats(self, mock_client):
        expected = [0.1] * 1536
        mock_client.embeddings.create.return_value = self._make_mock_response(expected)
        result = embed_query("how does authentication work?")
        assert result == expected

    @patch("app.rag.embeddings.client")
    def test_calls_api_with_query_text(self, mock_client):
        mock_client.embeddings.create.return_value = self._make_mock_response([0.1] * 1536)
        embed_query("what does fetch_repo do?")
        call_kwargs = mock_client.embeddings.create.call_args
        assert call_kwargs.kwargs["input"] == "what does fetch_repo do?"

    @patch("app.rag.embeddings.client")
    def test_calls_api_with_correct_model(self, mock_client):
        from app.config import settings
        mock_client.embeddings.create.return_value = self._make_mock_response([0.1] * 1536)
        embed_query("query")
        call_kwargs = mock_client.embeddings.create.call_args
        assert call_kwargs.kwargs["model"] == settings.embedding_model

    @patch("app.rag.embeddings.client")
    def test_returns_first_embedding_only(self, mock_client):
        expected = [0.9] * 1536
        mock_client.embeddings.create.return_value = self._make_mock_response(expected)
        result = embed_query("find the main class")
        assert result == expected
