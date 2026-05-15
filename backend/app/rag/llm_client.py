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
