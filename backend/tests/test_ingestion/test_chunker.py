from app.ingestion.chunker import extract_chunks
from app.ingestion.parser import parse_file

PYTHON_SOURCE = """\
import os
from pathlib import Path

def greet(name: str) -> str:
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    return a + b

class Dog:
    def __init__(self, name: str):
        self.name = name

    def bark(self) -> str:
        return "Woof!"
"""

TYPESCRIPT_SOURCE = """\
import { useState } from 'react';
import axios from 'axios';

function greet(name: string): string {
    return `Hello, ${name}!`;
}

const add = (a: number, b: number): number => a + b;

class Dog {
    name: string;
    constructor(name: string) {
        this.name = name;
    }
    bark(): string {
        return 'Woof!';
    }
}
"""

class TestExtractChunks:
    def test_returns_empty_list_for_none(self):
        assert extract_chunks(None) == []

    def test_extracts_python_functions(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        function_chunks = [c for c in chunks if c["chunk_type"] == "function"]
        names = [c["name"] for c in function_chunks]
        assert "greet" in names
        assert "add" in names

    def test_extracts_python_class(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        class_chunks = [c for c in chunks if c["chunk_type"] == "class"]
        assert len(class_chunks) == 1
        assert class_chunks[0]["name"] == "Dog"

    def test_extracts_python_imports(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        import_chunks = [c for c in chunks if c["chunk_type"] == "imports"]
        assert len(import_chunks) == 1
        assert "import os" in import_chunks[0]["content"]
        assert "from pathlib import Path" in import_chunks[0]["content"]

    def test_imports_chunk_is_first(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        assert chunks[0]["chunk_type"] == "imports"

    def test_chunk_has_correct_file_path(self):
        parsed = parse_file("src/main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        for chunk in chunks:
            assert chunk["file_path"] == "src/main.py"

    def test_chunk_has_line_numbers(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        for chunk in chunks:
            assert "start_line" in chunk
            assert "end_line" in chunk
            assert chunk["start_line"] >= 1
            assert chunk["end_line"] >= chunk["start_line"]

    def test_chunk_content_is_not_empty(self):
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        for chunk in chunks:
            assert chunk["content"].strip() != ""

    def test_class_chunk_does_not_duplicate_methods(self):
        # the class chunk should be one chunk, methods inside should not be separate chunks
        parsed = parse_file("main.py", PYTHON_SOURCE)
        chunks = extract_chunks(parsed)
        names = [c["name"] for c in chunks]
        # __init__ and bark are methods inside Dog — they should not appear as separate chunks
        assert "__init__" not in names
        assert "bark" not in names

    def test_extracts_typescript_function(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        function_chunks = [c for c in chunks if c["chunk_type"] == "function"]
        names = [c["name"] for c in function_chunks]
        assert "greet" in names

    def test_extracts_typescript_arrow_function(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        function_chunks = [c for c in chunks if c["chunk_type"] == "function"]
        # arrow function — name may be None for anonymous but content should contain 'add'
        contents = [c["content"] for c in function_chunks]
        assert any("add" in c for c in contents)

    def test_extracts_typescript_class(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        class_chunks = [c for c in chunks if c["chunk_type"] == "class"]
        assert any(c["name"] == "Dog" for c in class_chunks)

    def test_extracts_typescript_imports(self):
        parsed = parse_file("app.ts", TYPESCRIPT_SOURCE)
        chunks = extract_chunks(parsed)
        import_chunks = [c for c in chunks if c["chunk_type"] == "imports"]
        assert len(import_chunks) == 1
        assert "useState" in import_chunks[0]["content"]

    def test_returns_empty_list_for_empty_file(self):
        parsed = parse_file("main.py", "")
        chunks = extract_chunks(parsed)
        assert chunks == []

    def test_returns_only_imports_chunk_for_imports_only_file(self):
        source = "import os\nimport sys\n"
        parsed = parse_file("main.py", source)
        chunks = extract_chunks(parsed)
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "imports"