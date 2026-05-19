from unittest.mock import MagicMock, patch

from app.rag.retriever import retrieve_chunks


def _make_mock_row(
    id=1,
    chunk_type="function",
    name="my_func",
    content="def my_func(): pass",
    start_line=1,
    end_line=3,
    file_path="app/main.py",
    distance=0.15,
):
    row = MagicMock()
    row.id = id
    row.chunk_type = chunk_type
    row.name = name
    row.content = content
    row.start_line = start_line
    row.end_line = end_line
    row.file_path = file_path
    row.distance = distance
    return row


def _make_mock_db(rows):
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = rows
    return mock_db


# --- retrieve_chunks tests ---

class TestRetrieveChunks:
    @patch("app.rag.retriever.embed_query")
    def test_calls_embed_query_with_query_text(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        db = _make_mock_db([])
        retrieve_chunks("how does auth work?", repo_id=1, db=db)
        mock_embed.assert_called_once_with("how does auth work?")

    @patch("app.rag.retriever.embed_query")
    def test_returns_empty_list_when_no_rows(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        db = _make_mock_db([])
        result = retrieve_chunks("query", repo_id=1, db=db)
        assert result == []

    @patch("app.rag.retriever.embed_query")
    def test_returns_one_result_per_row(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        rows = [_make_mock_row(id=1), _make_mock_row(id=2)]
        db = _make_mock_db(rows)
        result = retrieve_chunks("query", repo_id=1, db=db)
        assert len(result) == 2

    @patch("app.rag.retriever.embed_query")
    def test_result_contains_expected_keys(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        db = _make_mock_db([_make_mock_row()])
        result = retrieve_chunks("query", repo_id=1, db=db)
        expected_keys = {"id", "chunk_type", "name", "content", "start_line", "end_line", "file_path", "distance"}
        assert set(result[0].keys()) == expected_keys

    @patch("app.rag.retriever.embed_query")
    def test_result_maps_row_fields_correctly(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        row = _make_mock_row(
            id=42,
            chunk_type="class",
            name="MyClass",
            content="class MyClass: pass",
            start_line=5,
            end_line=10,
            file_path="app/models.py",
            distance=0.22,
        )
        db = _make_mock_db([row])
        result = retrieve_chunks("query", repo_id=1, db=db)
        assert result[0] == {
            "id": 42,
            "chunk_type": "class",
            "name": "MyClass",
            "content": "class MyClass: pass",
            "start_line": 5,
            "end_line": 10,
            "file_path": "app/models.py",
            "distance": 0.22,
        }

    @patch("app.rag.retriever.embed_query")
    def test_passes_repo_id_to_db(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        db = _make_mock_db([])
        retrieve_chunks("query", repo_id=7, db=db)
        call_args = db.execute.call_args
        assert call_args[0][1]["repo_id"] == 7

    @patch("app.rag.retriever.embed_query")
    def test_passes_top_k_to_db(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        db = _make_mock_db([])
        retrieve_chunks("query", repo_id=1, db=db, top_k=5)
        call_args = db.execute.call_args
        assert call_args[0][1]["top_k"] == 5

    @patch("app.rag.retriever.embed_query")
    def test_default_top_k_is_15(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        db = _make_mock_db([])
        retrieve_chunks("query", repo_id=1, db=db)
        call_args = db.execute.call_args
        assert call_args[0][1]["top_k"] == 15

    @patch("app.rag.retriever.embed_query")
    def test_passes_query_vector_to_db(self, mock_embed):
        vector = [0.5] * 1536
        mock_embed.return_value = vector
        db = _make_mock_db([])
        retrieve_chunks("query", repo_id=1, db=db)
        call_args = db.execute.call_args
        assert call_args[0][1]["query_vector"] == str(vector)

    @patch("app.rag.retriever.embed_query")
    def test_executes_db_query_once(self, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        db = _make_mock_db([])
        retrieve_chunks("query", repo_id=1, db=db)
        db.execute.assert_called_once()
