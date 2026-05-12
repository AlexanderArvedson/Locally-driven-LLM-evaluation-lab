# This file defines the core data structures and main class for the repository intelligence system.
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

# The FileNode dataclass represents a file in the repository, 
# including its path, language, size, and whether it's a test file.
@dataclass(frozen=True)
class FileNode:
    path: str
    language: str
    size: int
    is_test: bool

# The Symbol dataclass represents a symbol in the repository, 
# including its ID, name, kind, and location information.
@dataclass(frozen=True)
class Symbol:
    id: str
    name: str
    kind: str
    file_path: str
    start_line: int
    end_line: int
    parent_symbol: str | None = None

# The RepositorySnapshot dataclass represents a snapshot of the repository,
@dataclass(frozen=True)
class RepositorySnapshot:
    repo_path: str
    files: list[FileNode]
    symbols: list[Symbol]

# The RepoIntel class is the main entry point for analyzing a repository.
class RepoIntel:
    def __init__(self, repo_path: str | Path, db_path: str | Path):
        from .index import RepositoryIndex

        self.repo_path = Path(repo_path)
        self.db_path = Path(db_path)
        self.repository_index = RepositoryIndex(self.db_path)

    def rebuild(self) -> RepositorySnapshot:
        from .extraction import extract_symbols
        from .parsing import parse_file
        from .scanner import scan_repository

        files = scan_repository(self.repo_path)
        symbols: list[Symbol] = []

        for file_node in files:
            if file_node.language != "python":
                continue
            parsed_file = parse_file(self.repo_path / file_node.path)
            parsed_file = replace(parsed_file, path=file_node.path)
            symbols.extend(extract_symbols(parsed_file))

        snapshot = RepositorySnapshot(repo_path=str(self.repo_path), files=files, symbols=symbols)
        self.repository_index.rebuild(snapshot)
        return snapshot

    def find_symbol(self, name: str):
        return self.repository_index.find_symbol(name)
