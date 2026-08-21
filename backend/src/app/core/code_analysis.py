from dataclasses import dataclass, field

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from app.core.sandbox import Sandbox

PY_LANGUAGE = Language(tspython.language())


@dataclass
class FileStructure:
    """A structural summary of one source file — the shape of it, not
    its full content. This is what we hand to an LLM later instead of
    the raw file: enough to reason about, far fewer tokens.
    """

    path: str
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def parse_python_file(path: str, source_code: str) -> FileStructure:
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(bytes(source_code, "utf-8"))
    root = tree.root_node

    structure = FileStructure(path=path)

    def walk(node: Node) -> None:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text:
                structure.functions.append(name_node.text.decode("utf-8"))

        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text:
                structure.classes.append(name_node.text.decode("utf-8"))

        elif node.type in ("import_statement", "import_from_statement"):
            structure.imports.append(source_code[node.start_byte : node.end_byte])

        for child in node.children:
            walk(child)

    walk(root)
    return structure


@dataclass
class RepositoryMap:
    """The full structural summary of a repository — what Phase 5's
    Investigator will actually work from, instead of a raw file tree.
    """

    files: list[FileStructure] = field(default_factory=list)

    def summary(self) -> str:
        """A compact, human/LLM-readable text summary. This — not the
        raw file list — is what actually gets put into a prompt later.
        """
        lines = []
        for f in self.files:
            lines.append(f"{f.path}")
            if f.classes:
                lines.append(f"  classes: {', '.join(f.classes)}")
            if f.functions:
                lines.append(f"  functions: {', '.join(f.functions)}")
        return "\n".join(lines)


def build_repository_map(sandbox: Sandbox) -> RepositoryMap:
    """Walk every Python file in the sandboxed repo and build a
    structural map — deterministic, no LLM involved, cheap to compute.
    """
    file_paths = sandbox.list_source_files(extensions=["py"])

    repo_map = RepositoryMap()
    for relative_path in file_paths:
        full_path = f"/workspace/repo/{relative_path}"
        content = sandbox.read_file(full_path)
        if content is None:
            continue  # file vanished or unreadable — skip, don't crash the whole map

        structure = parse_python_file(relative_path, content)
        repo_map.files.append(structure)

    return repo_map
