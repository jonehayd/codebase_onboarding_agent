from app.ingestion.filter import should_include

class TestShouldInclude:
    def test_includes_python_file(self):
        assert should_include("src/main.py", 1000) is True

    def test_includes_typescript_file(self):
        assert should_include("src/components/App.tsx", 5000) is True

    def test_includes_javascript_file(self):
        assert should_include("src/index.js", 2000) is True

    def test_includes_java_file(self):
        assert should_include("src/Main.java", 3000) is True

    def test_includes_go_file(self):
        assert should_include("main.go", 1500) is True

    def test_excludes_file_over_size_limit(self):
        assert should_include("src/main.py", 200_000) is False

    def test_excludes_file_exactly_at_size_limit(self):
        assert should_include("src/main.py", 100_001) is False

    def test_includes_file_exactly_at_size_limit(self):
        assert should_include("src/main.py", 100_000) is True

    def test_excludes_node_modules(self):
        assert should_include("node_modules/lodash/index.js", 1000) is False

    def test_excludes_nested_node_modules(self):
        assert should_include("packages/app/node_modules/react/index.js", 1000) is False

    def test_excludes_git_directory(self):
        assert should_include(".git/config", 500) is False

    def test_excludes_dist_directory(self):
        assert should_include("dist/bundle.js", 1000) is False

    def test_excludes_build_directory(self):
        assert should_include("build/main.py", 1000) is False

    def test_excludes_pycache(self):
        assert should_include("app/__pycache__/main.cpython-311.pyc", 1000) is False

    def test_excludes_package_lock(self):
        assert should_include("package-lock.json", 50000) is False

    def test_excludes_yarn_lock(self):
        assert should_include("yarn.lock", 50000) is False

    def test_excludes_poetry_lock(self):
        assert should_include("poetry.lock", 50000) is False

    def test_excludes_unknown_extension(self):
        assert should_include("src/binary.exe", 1000) is False

    def test_excludes_file_with_no_extension(self):
        assert should_include("Makefile", 1000) is False

    def test_includes_deeply_nested_valid_file(self):
        assert should_include("src/services/auth/handlers/login.ts", 5000) is True

    def test_excludes_venv_directory(self):
        assert should_include(".venv/lib/python3.11/site-packages/requests/__init__.py", 1000) is False