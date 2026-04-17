from collections.abc import Generator

import anthropic

from app.config import settings

client = anthropic.Client(api_key=settings.anthropic_key)

def stream_responses(prompt: str) -> Generator[str, None, None]:
    """Stream a response from the Anthropic API.

    Args:
        prompt (str): The fully assembled prompt from prompt_builder.

    Yields:
        str: Text tokens as they stream from the API.
    """
    
    with client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=settings.max_response_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text

def get_response(prompt: str) -> str:
    """Get a complete non-streamed response from the Anthropic API.
    Useful for testing and background tasks where streaming isn't needed.

    Args:
        prompt (str): The fully assembled prompt from prompt_builder.

    Returns:
        str: The complete response text.
    """
    
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.max_response_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# --- manual test code for LLM client ---
if __name__ == "__main__":
    from app.rag.prompt_builder import build_prompt

    mock_chunks = [
        {
            "chunk_type": "function",
            "name": "get_user_by_id",
            "content": "def get_user_by_id(db, user_id: int):\n    return db.query(User).filter(User.id == user_id).first()",
            "start_line": 12,
            "end_line": 14,
            "file_path": "app/services/user_service.py",
            "distance": 0.12,
        },
        {
            "chunk_type": "class",
            "name": "User",
            "content": "class User(Base):\n    __tablename__ = 'users'\n    id = Column(Integer, primary_key=True)\n    email = Column(String, unique=True)",
            "start_line": 5,
            "end_line": 10,
            "file_path": "app/db/models.py",
            "distance": 0.21,
        },
    ]

    query = "How do I fetch a user from the database?"
    prompt = build_prompt(query, mock_chunks)

    print("=== Non-streamed response ===")
    response = get_response(prompt)
    print(response)

    print("\n=== Streamed response ===")
    for token in stream_responses(prompt):
        print(token, end="", flush=True)
    print()