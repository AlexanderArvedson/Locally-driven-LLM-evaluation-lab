from pathlib import Path

from repo_intel.extraction import extract_symbols
from repo_intel.parsing import parse_file


def test_parse_and_extract_python_symbols():
    file_path = Path("/home/alexa/projects/examensarbete/Locally-driven-LLM/data/repos/basic_python_repo/sample_module.py")
    parsed_file = parse_file(file_path)
    symbols = extract_symbols(parsed_file)

    assert [symbol.name for symbol in symbols] == ["helper", "UserService", "create_user", "build_report"]
    assert symbols[0].kind == "function"
    assert symbols[1].kind == "class"
    assert symbols[2].parent_symbol == "UserService"
    assert symbols[3].start_line == 10
