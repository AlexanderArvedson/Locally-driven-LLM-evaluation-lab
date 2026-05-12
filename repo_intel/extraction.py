# This file contains the main logic for extracting symbols from parsed source code files, 
# using the syntax tree produced by tree-sitter to identify classes and functions, 
# and building Symbol objects with stable IDs based on their location in the source code.
from __future__ import annotations

from hashlib import sha1

from .core import Symbol
from .parsing import ParsedFile

# This function generates a stable symbol ID based on the file path, symbol name, kind, and location in the source code, using a SHA-1 hash of this information.
def _stable_symbol_id(file_path: str, name: str, kind: str, start_line: int, end_line: int) -> str:
    payload = f"{file_path}:{name}:{kind}:{start_line}:{end_line}".encode("utf-8")
    return sha1(payload).hexdigest()

# This function extracts symbols from a parsed source code file by traversing the syntax tree
#  and identifying class and function definitions, building Symbol objects for each identified symbol.
def _node_name(node, source_bytes: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None
    return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")

# This function recursively traverses the syntax tree of a parsed source code file, extracting class 
# and function definitions and building Symbol objects for each identified symbol, while maintaining the parent-child relationships between symbols.
def _extract_from_node(node, source_bytes: bytes, file_path: str, parent_symbol: str | None, symbols: list[Symbol]) -> None:
    if node.type == "class_definition":
        name = _node_name(node, source_bytes)
        if name:
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1
            symbols.append(
                Symbol(
                    id=_stable_symbol_id(file_path, name, "class", start_line, end_line),
                    name=name,
                    kind="class",
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    parent_symbol=parent_symbol,
                )
            )
            parent_symbol = name

    if node.type == "function_definition":
        name = _node_name(node, source_bytes)
        if name:
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1
            symbols.append(
                Symbol(
                    id=_stable_symbol_id(file_path, name, "function", start_line, end_line),
                    name=name,
                    kind="function",
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    parent_symbol=parent_symbol,
                )
            )

    for child in node.named_children:
        _extract_from_node(child, source_bytes, file_path, parent_symbol, symbols)

# This is the main function that extracts symbols from a parsed source code file by traversing the syntax tree
def extract_symbols(parsed_file: ParsedFile) -> list[Symbol]:
    symbols: list[Symbol] = []
    _extract_from_node(parsed_file.tree.root_node, parsed_file.source_bytes, parsed_file.path, None, symbols)
    return sorted(symbols, key=lambda symbol: (symbol.file_path, symbol.start_line, symbol.end_line, symbol.name))
