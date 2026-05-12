# This file contains the main logic for scanning a repository and building a list of FileNode objects representing the files in the repository, 
# while respecting .gitignore patterns and default ignored directories.
from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from .core import FileNode

# Default directories to ignore when scanning the repository, in addition to .gitignore patterns.
DEFAULT_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "ENV",
    "build",
    "dist",
    "node_modules",
    ".tox",
    ".nox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

# Mapping of file extensions to programming languages for language detection.
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}

# This function loads .gitignore patterns from the repository root, if the .gitignore file exists.
def _load_gitignore_patterns(repo_root: Path) -> list[str]:
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        return []

    patterns: list[str] = []
    for line in gitignore.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)
    return patterns

# This function checks if a given relative path should be ignored based on the .gitignore patterns and default ignored directories.
def _is_ignored(relative_path: Path, patterns: list[str]) -> bool:
    path_str = relative_path.as_posix()
    parts = relative_path.parts

    if any(part in DEFAULT_IGNORED_DIRS for part in parts):
        return True

    if relative_path.name.startswith(".") and relative_path.name in DEFAULT_IGNORED_DIRS:
        return True

    for pattern in patterns:
        if pattern.endswith("/"):
            prefix = pattern.rstrip("/")
            if path_str == prefix or path_str.startswith(prefix + "/"):
                return True
            continue
        if "/" in pattern:
            if fnmatch(path_str, pattern):
                return True
            continue
        if fnmatch(relative_path.name, pattern):
            return True
        if any(fnmatch(part, pattern) for part in parts):
            return True
    return False

# This function detects the programming language of a file based on its extension using the LANGUAGE_EXTENSIONS mapping.
def detect_language(file_path: Path) -> str | None:
    return LANGUAGE_EXTENSIONS.get(file_path.suffix.lower())

# This function determines if a file is a test file based on its path and name, using common conventions for test files.
def is_test_file(relative_path: Path) -> bool:
    parts = [part.lower() for part in relative_path.parts]
    name = relative_path.name.lower()
    return any(part == "tests" or part.startswith("test") for part in parts) or name.startswith("test_") or name.endswith("_test.py")

# This is the main function that scans the repository at the given path and returns a list of FileNode objects representing the files in the repository,
def scan_repository(repo_path: str | Path) -> list[FileNode]:
    root = Path(repo_path).resolve()
    patterns = _load_gitignore_patterns(root)
    files: list[FileNode] = []

    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root)
        if _is_ignored(relative_path, patterns):
            continue
        language = detect_language(path)
        if language is None:
            continue
        files.append(
            FileNode(
                path=relative_path.as_posix(),
                language=language,
                size=path.stat().st_size,
                is_test=is_test_file(relative_path),
            )
        )

    return files
