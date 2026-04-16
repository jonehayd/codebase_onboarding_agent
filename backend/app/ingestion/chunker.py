from tree_sitter import Node

from app.ingestion.parser import ParsedFile

# node types in the tree-sitter AST vary by language
# we define sets of node types that correspond to code chunks (e.g. functions, classes) and imports for each language
CHUNK_NODE_TYPES = {
    "py":   {"function_definition", "class_definition"},
    "js":   {"function_declaration", "function_expression", "arrow_function", "class_declaration", "method_definition"},
    "jsx":  {"function_declaration", "function_expression", "arrow_function", "class_declaration", "method_definition"},
    "ts":   {"function_declaration", "function_expression", "arrow_function", "class_declaration", "method_definition"},
    "tsx":  {"function_declaration", "function_expression", "arrow_function", "class_declaration", "method_definition"},
    "java": {"method_declaration", "class_declaration", "constructor_declaration"},
    "go":   {"function_declaration", "method_declaration", "type_declaration"},
}

IMPORT_NODE_TYPES = {
    "py":   {"import_statement", "import_from_statement"},
    "js":   {"import_statement", "import_declaration"},
    "jsx":  {"import_statement", "import_declaration"},
    "ts":   {"import_statement", "import_declaration"},
    "tsx":  {"import_statement", "import_declaration"},
    "java": {"import_declaration"},
    "go":   {"import_declaration", "import_spec"},
}

def get_node_name(node: Node, source: bytes) -> str:
    """Extract the name of a code chunk from a tree-sitter AST node.

    Args:
        node (Node): The tree-sitter AST node representing the code chunk.
        source (bytes): The original source code as bytes.

    Returns:
        str | None: The extracted name of the code chunk, or None if it cannot be determined.
    """
    
    name_node = node.child_by_field_name("name")
    if name_node:
        return source[name_node.start_byte:name_node.end_byte].decode("utf-8")
    return None

def extract_chunks(parsed: ParsedFile) -> list[dict]:
    """Extract code chunks from a parsed file.

    Args:
        parsed (ParsedFile): An instance of ParsedFile containing the file path, language, AST, and content.
    Returns:
        list[dict]: A list of dictionaries, each representing a code chunk with its type, name, content, and line numbers.
    """
    
    if parsed is None:
        return []

    language = parsed.language_ext
    source = parsed.content.encode("utf-8")
    file_path = parsed.file_path
    root = parsed.tree.root_node
    
    chunk_types = CHUNK_NODE_TYPES.get(language, set())
    import_types = IMPORT_NODE_TYPES.get(language, set())
    
    chunks = []
    imports = []
    
    def walk(node: Node):
        """Recursively walk the AST and extract code chunks and imports.

        Args:
            node (Node): The current AST node.
        """
        
        # Check if the current node is an import statement
        if node.type in import_types:
            imports.append(source[node.start_byte:node.end_byte].decode("utf-8"))
            return
        
        # Check if the current node is a code chunk (function, class, etc.)
        if node.type in chunk_types:
            name = get_node_name(node, source)
            content_node = node

            # For arrow functions, walk up to the lexical_declaration to capture "const add = ..."
            if node.type == "arrow_function" and name is None:
                parent = node.parent
                if parent and parent.type == "variable_declarator":
                    name_node = parent.child_by_field_name("name")
                    if name_node:
                        name = source[name_node.start_byte:name_node.end_byte].decode("utf-8")
                    if parent.parent and "declaration" in parent.parent.type:
                        content_node = parent.parent

            content = source[content_node.start_byte:content_node.end_byte].decode("utf-8")
            
            chunk_type = "class" if "class" in node.type else "function"
            
            chunks.append({
                "file_path": file_path,
                "chunk_type": chunk_type,
                "name": name,
                "content": content,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1
            })
            return
        
        for child in node.children:
            walk(child)
            
    walk(root)
    
    # group all imports into a single chunk at the top of the file
    if imports:
        chunks.insert(0, {
            "file_path": file_path,
            "chunk_type": "imports",
            "name": None,
            "content": "\n".join(imports),
            "start_line": 1,
            "end_line": len(imports),
        })
        
    return chunks