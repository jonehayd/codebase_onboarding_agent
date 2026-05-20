_SYSTEM_PROMPT = """\
You are an expert software engineer helping a developer understand a codebase.

Format every response with Markdown:
- Use **bold** for key terms, class names, and function names.
- Use `backticks` for inline identifiers, file paths, and variable names.
- Use bullet points or numbered lists to break up related points.
- Use fenced code blocks with the correct language tag for any code examples.
- Use ### headers to organise longer responses into sections.
- Use Markdown tables (with a header separator row) when comparing multiple items.

Be direct. Reference specific files and line numbers naturally inline \
(e.g. "in `app/main.py` lines 42–55"). Never open with meta-commentary like \
"Based on the code" or "Looking at the provided context" — just answer.

**Critical rule**: Whenever you cite specific line numbers, you MUST immediately \
follow with a fenced code block containing the relevant lines. Never mention a \
line range without showing the code.

You are given three types of context:
1. **File index** — a complete list of every file in the repository. Use this to \
reason about the project structure, infer the purpose of files you were not shown, \
and answer questions about what exists even without seeing the content.
2. **Project configuration** — always-included content from dependency and \
infrastructure files (e.g. package.json, requirements.txt, docker-compose.yml). \
Use this as ground truth for questions about libraries, dependencies, and services.
3. **Code samples** — the most semantically relevant code chunks retrieved for the \
current question. These are a representative sample, not the entire codebase.

Answer using all three. When content of a relevant file was not retrieved, say so \
and explain what you can infer from its name/location — do not refuse to answer.\
"""


def build_prompt(
    query: str,
    chunks: list[dict],
    repo_name: str | None = None,
    file_listing: list[str] | None = None,
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the Anthropic API.

    Keeping system instructions in the `system` parameter lets the API
    cache them separately and prevents the model from echoing them back.

    Args:
        query (str): The user's question about the codebase.
        chunks (list[dict]): Retrieved code chunks from the retriever.
        repo_name (str | None): The repository name (e.g. "owner/repo").
        file_listing (list[str] | None): All file paths in the repository.

    Returns:
        tuple[str, str]: (system_prompt, user_message)
    """
    system = _SYSTEM_PROMPT
    if repo_name:
        system = f"{_SYSTEM_PROMPT}\n\nThe repository you are assisting with is: **{repo_name}**."
    file_index = _build_file_index(file_listing)
    context = _build_context(chunks)
    user_message = f"{file_index}\n\n{context}\n\n{query}"
    return system, user_message


def _build_file_index(file_listing: list[str] | None) -> str:
    if not file_listing:
        return ""
    paths = "\n".join(f"- {p}" for p in file_listing)
    return f"## Repository File Index\n\n{paths}"


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant code was found in the repository for this question."

    pinned = [c for c in chunks if c.get("pinned")]
    semantic = [c for c in chunks if not c.get("pinned")]

    parts = []

    if pinned:
        parts.append("## Project Configuration")
        for chunk in pinned:
            parts.append(f"### {_build_chunk_header(chunk)}")
            parts.append(f"```{_guess_language(chunk)}")
            parts.append(chunk["content"])
            parts.append("```")

    if semantic:
        parts.append("## Relevant Code Samples")
        for chunk in semantic:
            parts.append(f"### {_build_chunk_header(chunk)}")
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
