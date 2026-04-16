from app.ingestion.parser import parse_file, get_language, ParsedFile

class TestGetLanguage:
    def test_returns_language_for_python(self):
        assert get_language("main.py") is not None

    def test_returns_language_for_typescript(self):
        assert get_language("app.ts") is not None

    def test_returns_language_for_tsx(self):
        assert get_language("App.tsx") is not None

    def test_returns_language_for_javascript(self):
        assert get_language("index.js") is not None

    def test_returns_language_for_java(self):
        assert get_language("Main.java") is not None

    def test_returns_language_for_go(self):
        assert get_language("main.go") is not None

    def test_returns_none_for_unknown_extension(self):
        assert get_language("file.xyz")[0] is None

    def test_returns_none_for_no_extension(self):
        assert get_language("Makefile")[0] is None

    def test_handles_uppercase_extension(self):
        # extensions are lowercased so .PY should work
        assert get_language("main.PY") is not None

    def test_handles_nested_path(self):
        assert get_language("src/services/auth.py") is not None

    def test_handles_multiple_dots_in_filename(self):
        # rsplit on last dot — some.module.py should give "py"
        assert get_language("some.module.py") is not None


class TestParseFile:
    def test_returns_parsed_file_for_python(self):
        result = parse_file("main.py", "x = 1")
        assert result is not None
        assert isinstance(result, ParsedFile)

    def test_returns_none_for_unsupported_type(self):
        result = parse_file("file.xyz", "some content")
        assert result is None

    def test_parsed_file_has_correct_file_path(self):
        result = parse_file("src/main.py", "x = 1")
        assert result.file_path == "src/main.py"

    def test_parsed_file_has_content(self):
        source = "def hello(): pass"
        result = parse_file("main.py", source)
        assert result.content == source

    def test_parsed_file_has_tree(self):
        result = parse_file("main.py", "x = 1")
        assert result.tree is not None
        assert result.tree.root_node is not None

    def test_parsed_file_tree_has_no_errors(self):
        result = parse_file("main.py", "def greet(name):\n    return f'hello {name}'")
        assert not result.tree.root_node.has_error

    def test_parses_typescript(self):
        result = parse_file("app.ts", "const x: number = 1;")
        assert result is not None
        assert not result.tree.root_node.has_error

    def test_parses_javascript(self):
        result = parse_file("index.js", "const x = 1;")
        assert result is not None

    def test_parses_empty_file(self):
        result = parse_file("main.py", "")
        assert result is not None
        assert result.tree is not None