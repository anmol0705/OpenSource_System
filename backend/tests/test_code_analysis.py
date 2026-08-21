from app.core.code_analysis import parse_python_file


def test_parse_extracts_function_names() -> None:
    code = """
                def foo():
                    pass

                def bar(x, y):
                    return x + y
            """
    result = parse_python_file("sample.py", code)
    assert result.functions == ["foo", "bar"]


def test_parse_extracts_class_names() -> None:
    code = """
class Alpha:
    pass

class Beta:
    def method(self):
        pass
"""
    result = parse_python_file("sample.py", code)
    assert result.classes == ["Alpha", "Beta"]


def test_parse_extracts_method_inside_class() -> None:
    """The key test for the recursion behavior — a method nested inside
    a class should still be found, not just top-level functions.
    """
    code = """
class Widget:
    def render(self):
        pass
"""
    result = parse_python_file("sample.py", code)
    assert result.classes == ["Widget"]
    assert result.functions == ["render"]


def test_parse_extracts_imports() -> None:
    code = """
import os
from typing import Any
"""
    result = parse_python_file("sample.py", code)
    assert "import os" in result.imports
    assert "from typing import Any" in result.imports


def test_parse_handles_empty_file() -> None:
    result = parse_python_file("empty.py", "")
    assert result.functions == []
    assert result.classes == []
    assert result.imports == []
