from openai import OpenAI
import tiktoken
from app.config import settings

client = OpenAI(api_key=settings.open_ai_key)

_tokenizer = tiktoken.get_encoding("cl100k_base")
_MAX_EMBED_TOKENS = 8000  # hard limit is 8192; leave a small margin


def build_embed_text(chunk: dict) -> str:
    """Build the text to be embedded for a given code chunk.

    Args:
        chunk (dict): A dictionary representing a code chunk.

    Returns:
        str: The text to be embedded.
    """
    
    parts = []
    if chunk.get("name"):
        parts.append(f"{chunk['chunk_type']} {chunk['name']}")
    if chunk.get("content"):
        parts.append(chunk["content"])
    text = "\n".join(parts)
    tokens = _tokenizer.encode(text)
    if len(tokens) > _MAX_EMBED_TOKENS:
        text = _tokenizer.decode(tokens[:_MAX_EMBED_TOKENS])
    return text

_MAX_BATCH_TOKENS = 250_000  # OpenAI limit is 300k; leave headroom for safety


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

    results: list[list[float]] = []
    batch: list[str] = []
    batch_tokens = 0

    for text in texts:
        token_count = len(_tokenizer.encode(text))
        if batch and batch_tokens + token_count > _MAX_BATCH_TOKENS:
            response = client.embeddings.create(input=batch, model=settings.embedding_model)
            results.extend(d.embedding for d in response.data)
            batch = []
            batch_tokens = 0
        batch.append(text)
        batch_tokens += token_count

    if batch:
        response = client.embeddings.create(input=batch, model=settings.embedding_model)
        results.extend(d.embedding for d in response.data)

    return results

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