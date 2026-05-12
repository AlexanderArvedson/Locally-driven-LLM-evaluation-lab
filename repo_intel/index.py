# This file contains the RepositoryIndex class, which manages a SQLite database to store information about source code files and their symbols,
#  allowing for efficient querying of symbols by name. The index can be rebuilt from a RepositorySnapshot, 
# which contains the current state of the repository's files and symbols.
from __future__ import annotations

import sqlite3
from pathlib import Path

from .core import RepositorySnapshot, Symbol


SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    language TEXT NOT NULL,
    size INTEGER NOT NULL,
    is_test INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS symbols (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    parent_symbol TEXT,
    FOREIGN KEY(file_path) REFERENCES files(path)
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file_path ON symbols(file_path);
"""

# The RepositoryIndex class manages a SQLite database to store information about source code files and their symbols, allowing for efficient querying of symbols by name.
class RepositoryIndex:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def rebuild(self, snapshot: RepositorySnapshot) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            connection.execute("DELETE FROM symbols")
            connection.execute("DELETE FROM files")
            connection.executemany(
                "INSERT INTO files(path, language, size, is_test) VALUES (?, ?, ?, ?)",
                ((file.path, file.language, file.size, int(file.is_test)) for file in snapshot.files),
            )
            connection.executemany(
                "INSERT INTO symbols(id, name, kind, file_path, start_line, end_line, parent_symbol) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    (
                        symbol.id,
                        symbol.name,
                        symbol.kind,
                        symbol.file_path,
                        symbol.start_line,
                        symbol.end_line,
                        symbol.parent_symbol,
                    )
                    for symbol in snapshot.symbols
                ),
            )
            connection.commit()

    def find_symbol(self, name: str) -> list[Symbol]:
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            rows = connection.execute(
                """
                SELECT id, name, kind, file_path, start_line, end_line, parent_symbol
                FROM symbols
                WHERE name = ?
                ORDER BY file_path, start_line, end_line, id
                """,
                (name,),
            ).fetchall()

        return [
            Symbol(
                id=row["id"],
                name=row["name"],
                kind=row["kind"],
                file_path=row["file_path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                parent_symbol=row["parent_symbol"],
            )
            for row in rows
        ]
