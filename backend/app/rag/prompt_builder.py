_SYSTEM_PROMPT = """\
You are an expert software engineer helping a developer understand a codebase.

Format every response with Markdown:
- Use **bold** for key terms, class names, and function names.
- Use `backticks` for inline identifiers, file paths, and variable names.
- Use bullet points or numbered lists to break up related points.
- Use fenced code blocks with the correct language tag for any code examples.
- Use ### headers to organise longer responses into sections.

Be direct. Reference specific files and line numbers naturally inline \
(e.g. "in `app/main.py` line 42"). Never open with meta-commentary like \
"Based on the code" or "Looking at the provided context" — just answer.\
"""


def build_prompt(query: str, chunks: list[dict], repo_name: str | None = None) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the Anthropic API.

    Keeping system instructions in the `system` parameter lets the API
    cache them separately and prevents the model from echoing them back.

    Args:
        query (str): The user's question about the codebase.
        chunks (list[dict]): Retrieved code chunks from the retriever.
        repo_name (str | None): The repository name (e.g. "owner/repo").

    Returns:
        tuple[str, str]: (system_prompt, user_message)
    """
    system = _SYSTEM_PROMPT
    if repo_name:
        system = f"{_SYSTEM_PROMPT}\n\nThe repository you are assisting with is: **{repo_name}**."
    context = _build_context(chunks)
    user_message = f"{context}\n\n{query}"
    return system, user_message


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant code was found in the repository for this question."

    parts = []
    for chunk in chunks:
        header = _build_chunk_header(chunk)
        parts.append(f"### {header}")
        parts.append(f"```{_guess_language(chunk)}")
        parts.append(chunk["content"])
        parts.append("```")

    return "\n".join(parts)


def _build_chunk_header(chunk: dict) -> str:
    file_path = chunk.get("file_path", "unknown")
    start_line = chunk.get("start_line", "?")
    end_line = chunk.get("end_line", "?")
    chunk_type = chunk.get("chunk_type", "")
    name = chunk.get("name")

    location = f"`{file_path}` lines {start_line}–{end_line}"
    if name:
        return f"{location} ({chunk_type} `{name}`)"
    return location


def _guess_language(chunk: dict) -> str:
    """Infer a fenced-code language tag from the file extension."""
    path = chunk.get("file_path", "")
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "py": "python", "js": "javascript", "ts": "typescript",
        "jsx": "jsx", "tsx": "tsx", "go": "go", "rs": "rust",
        "java": "java", "cpp": "cpp", "c": "c", "cs": "csharp",
        "rb": "ruby", "php": "php", "swift": "swift", "kt": "kotlin",
        "sh": "bash", "yaml": "yaml", "yml": "yaml", "json": "json",
        "md": "markdown", "sql": "sql", "html": "html", "css": "css",
    }.get(ext, "text")
