def build_prompt(query: str, chunks: list[dict]) -> str:
    """Build a prompt for the LLM from a query and retrieved code chunks.

    Args:
        query (str): The user's question about the codebase.
        chunks (list[dict]): Retrieved code chunks from the retriever.

    Returns:
        str: The fully assembled prompt to send to the LLM.
    """
    
    context = _build_context(chunks)
    
    return f"""You are an expert software engineer helping a developer understand a codebase.
You are given relevant code snippets retrieved from the repository, along with the developer's question.
Answer the question clearly and concisely based on the provided code.
If the answer cannot be determined from the provided code, say so honestly rather than guessing.
When referencing specific code, mention the file path and line numbers.

    {context}
    
    Question: {query}
    
    Answer:"""
    
def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a readable context block.

    Args:
        chunks (list[dict]): Retrieved code chunks from the retriever.

    Returns:
        str: Formatted context string.
    """
    
    if not chunks:
        return "No relevant code snippets were found in the repository."
    
    parts = ["Relevant code snippets from the repository:"]
    
    for i, chunk in enumerate(chunks, start=1):
        header = _build_chunk_header(chunk)
        parts.append(f"\n--- Snippet {i}: {header} ---")
        parts.append(chunk["content"])
    
    return "\n".join(parts)

def _build_chunk_header(chunk: dict) -> str:
    """Build a descriptive header for a code chunk.

    Args:
        chunk (dict): A code chunk dict from the retriever.

    Returns:
        str: A short header string describing the chunk.
    """
    
    file_path = chunk.get("file_path", "unknown file")
    start_line = chunk.get("start_line", "?")
    end_line = chunk.get("end_line", "?")
    chunk_type = chunk.get("chunk_type", "")
    name = chunk.get("name")
    
    location = f"{file_path} lines {start_line}-{end_line}"
    
    if name:
        return f"{chunk_type} `{name}` in {location}"
    
    return location


# --- manual test code ---
if __name__ == "__main__":
    mock_chunks = [
        {
            "id": 1,
            "chunk_type": "function",
            "name": "get_user_by_id",
            "content": "def get_user_by_id(db, user_id: int):\n    return db.query(User).filter(User.id == user_id).first()",
            "start_line": 12,
            "end_line": 14,
            "file_path": "app/services/user_service.py",
            "distance": 0.12,
        },
        {
            "id": 2,
            "chunk_type": "class",
            "name": "User",
            "content": "class User(Base):\n    __tablename__ = 'users'\n    id = Column(Integer, primary_key=True)\n    email = Column(String, unique=True)",
            "start_line": 5,
            "end_line": 10,
            "file_path": "app/db/models.py",
            "distance": 0.21,
        },
        {
            "id": 3,
            "chunk_type": "imports",
            "name": None,
            "content": "from sqlalchemy import Column, Integer, String\nfrom app.db.database import Base",
            "start_line": 1,
            "end_line": 2,
            "file_path": "app/db/models.py",
            "distance": 0.35,
        },
    ]

    query = "How do I fetch a user from the database?"
    prompt = build_prompt(query, mock_chunks)
    print(prompt)