# This file contains the main logic for parsing source code files in the repository using tree-sitter, and 
# building ParsedFile objects that contain the file path, detected language, source bytes, and parsed syntax tree.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_intel.scanner import detect_language

# The ParsedFile dataclass represents a parsed source code file, including its path, detected language, source bytes, and parsed syntax tree.
@dataclass(frozen=True)
class ParsedFile:
    path: str
    language: str
    source_bytes: bytes
    tree: Any

# This function builds a tree-sitter language object for the given language name, currently only supporting Python.
def _build_language(language_name: str):
    if language_name != "python":
        raise ValueError(f"Unsupported language for v1 parser: {language_name}")

    try:
        import tree_sitter_python
        from tree_sitter import Language

        language_factory = getattr(tree_sitter_python, "language", None)
        if language_factory is None:
            raise ImportError("tree_sitter_python.language is unavailable")

        raw_language = language_factory()
        try:
            return Language(raw_language)
        except TypeError:
            return raw_language
    except Exception as error:
        raise ImportError("Python tree-sitter bindings are not available") from error

# This function builds a tree-sitter parser for the given language name, currently only supporting Python.
def _build_parser(language_name: str):
    from tree_sitter import Parser

    parser = Parser()
    language = _build_language(language_name)

    try:
        parser.language = language
    except AttributeError:
        print("ERROR: could not set parser.language")
    return parser

# This function parses a source code file at the given path and returns a ParsedFile object containing the file path, detected language, source bytes, and parsed syntax tree.
def parse_file(file_path: str | Path) -> ParsedFile:
    path = Path(file_path)
    language = detect_language(path)
    if language is None:
        raise ValueError(f"Unsupported file type: {path}")

    parser = _build_parser(language)
    source_bytes = path.read_bytes()
    tree = parser.parse(source_bytes)
    return ParsedFile(path=path.as_posix(), language=language, source_bytes=source_bytes, tree=tree)
