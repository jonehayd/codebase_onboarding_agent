from collections.abc import Generator

import anthropic

from app.config import settings

client = anthropic.Client(api_key=settings.anthropic_key)


def stream_responses(system: str, user_message: str) -> Generator[str, None, None]:
    """Stream a response from the Anthropic API.

    Args:
        system (str): The system prompt (from prompt_builder).
        user_message (str): The assembled user turn (context + question).

    Yields:
        str: Text tokens as they stream from the API.
    """
    with client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=settings.max_response_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def expand_query(question: str) -> list[str]:
    """Return the original question plus up to 3 targeted sub-queries.

    Uses a cheap fast model so the extra round-trip has minimal latency impact.
    Falls back to [question] alone if the LLM call fails.
    """
    try:
        message = client.messages.create(
            model=settings.query_expansion_model,
            max_tokens=150,
            system=(
                "You are a code search expert. Given a question about a software codebase, "
                "generate 3 short, specific search queries that together cover the key aspects "
                "needed to answer the question. Queries will be used to search code embeddings, "
                "so make them concrete: include library names, function names, config keys, or "
                "technical concepts. Return exactly 3 queries, one per line, no numbering or "
                "extra explanation."
            ),
            messages=[{"role": "user", "content": question}],
        )
        sub_queries = [
            line.strip()
            for line in message.content[0].text.strip().splitlines()
            if line.strip()
        ]
        return [question] + sub_queries[:3]
    except Exception:
        return [question]


def get_response(system: str, user_message: str) -> str:
    """Get a complete non-streamed response. Useful for testing.

    Args:
        system (str): The system prompt.
        user_message (str): The assembled user turn.

    Returns:
        str: The complete response text.
    """
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.max_response_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text
