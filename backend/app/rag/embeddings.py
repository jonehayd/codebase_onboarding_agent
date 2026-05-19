from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.open_ai_key)

# ~4 chars/token on average; 30 000 chars keeps us well under the 8 192-token limit.
_MAX_EMBED_CHARS = 30_000

def build_embed_text(chunk: dict) -> str:
    """Build the text to be embedded for a given code chunk.

    Args:
        chunk (dict): A dictionary representing a code chunk.

    Returns:
        str: The text to be embedded.
    """
    
    # Build the text to be embedded by combining the chunk type, name, and content
    parts = []
    if chunk.get("name"):
        parts.append(f"{chunk['chunk_type']} {chunk['name']}")
    if chunk.get("content"):
        parts.append(chunk["content"])
    return "\n".join(parts)[:_MAX_EMBED_CHARS]

def embed_chunks(chunks: list[dict]) -> list[list[float]]:
    """Generate embeddings for a list of code chunks.

    Args:
        chunks (list[dict]): A list of dictionaries, each representing a code chunk.

    Returns:
        list[list[float]]: A list of embeddings, each corresponding to a code chunk.
    """
    if not chunks:
        return []
    
    texts = [build_embed_text(chunk) for chunk in chunks]
    
    response = client.embeddings.create(
        input=texts,
        model=settings.embedding_model
    )
    
    return [data.embedding for data in response.data]

def embed_query(query: str) -> list[float]:
    """Generate an embedding for a query string.

    Args:
        query (str): The input query string.

    Returns:
        list[float]: The embedding for the query string.
    """
    response = client.embeddings.create(
        input=query,
        model=settings.embedding_model
    )
    
    return response.data[0].embedding


# --- manual test code ---
if __name__ == "__main__":
    mock_chunk = {
        "chunk_type": "function",
        "name": "greet",
        "content": "def greet(name: str) -> str:\n    return f'Hello, {name}!'",
        "start_line": 1,
        "end_line": 2,
    }

    print("Embed text:")
    print(build_embed_text(mock_chunk))
    print()

    print("Embedding chunks...")
    vectors = embed_chunks([mock_chunk])
    print(f"Number of embeddings: {len(vectors)}")
    print(f"Dimensions: {len(vectors[0])}")
    print(f"First 5 values: {vectors[0][:5]}")
    print()

    print("Embedding query...")
    query_vector = embed_query("how do I greet someone?")
    print(f"Query dimensions: {len(query_vector)}")
    print(f"First 5 values: {query_vector[:5]}")