EXCLUDED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", ".env", "vendor", "target", "out"
}

INCLUDED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go",
    ".c", ".cpp", ".h", ".cs", ".rb", ".rs", ".swift",
    ".css", ".html", ".json", ".yaml", ".yml", ".toml",
    ".sql", ".sh", ".env.example"
}

EXCLUDED_FILES = {
    "package-lock.json", "yarn.lock", "poetry.lock",
    "Pipfile.lock", ".DS_Store"
}

def should_include(path: str, size: int) -> bool:
    """Determine if a file should be included based on its path and size.

    Args:
        path (str): The file path.
        size (int): The file size in bytes.

    Returns:
        bool: True if the file should be included, False otherwise.
    """
    
    if size > 100_000:  # Exclude files larger than 100 KB
        return False
    parts = path.split("/")
    if any(part in EXCLUDED_DIRS for part in parts):
        return False
    filename = parts[-1]
    if filename in EXCLUDED_FILES:
        return False
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in INCLUDED_EXTENSIONS:
        return False
    return True