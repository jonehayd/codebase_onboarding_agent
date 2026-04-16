from dataclasses import dataclass

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_java as tsjava
import tree_sitter_go as tsgo
from tree_sitter import Language, Parser, Tree

LANGUAGES = {
    "py":   Language(tspython.language()),
    "js":   Language(tsjavascript.language()),
    "jsx":  Language(tsjavascript.language()),
    "ts":   Language(tstypescript.language_typescript()),
    "tsx":  Language(tstypescript.language_tsx()),
    "java": Language(tsjava.language()),
    "go":   Language(tsgo.language()),
}

@dataclass
class ParsedFile:
    file_path: str
    language: Language
    language_ext: str
    tree: Tree
    content: str
    

def get_language(file_path: str):
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    return [LANGUAGES.get(ext, None), ext]

def parse_file(file_path: str, content: str) -> ParsedFile | None:
    """Parse a file and return its abstract syntax tree (AST) along with metadata.

    Args:
        file_path (str): The path to the file to be parsed.
        content (str): The content of the file to be parsed.

    Returns:
        ParsedFile | None: An instance of ParsedFile containing the file path, language, AST, and content, or None if the file type is unsupported.
    """
    
    language, ext = get_language(file_path)
    if not language:
        return None
    
    parser = Parser()
    parser.language = language
    tree = parser.parse(content.encode("utf-8"))
    
    return ParsedFile(
        file_path=file_path,
        language=language,
        language_ext=ext,
        tree=tree,
        content=content
    )