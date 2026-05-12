from pathlib import Path

from repo_intel.core import RepoIntel


def test_find_symbol_returns_file_and_line_range(tmp_path: Path):
    repo_root = Path("/home/alexa/projects/examensarbete/Locally-driven-LLM/data/repos/basic_python_repo")
    db_path = tmp_path / "index.sqlite"

    intel = RepoIntel(repo_root, db_path)
    intel.rebuild()

    helper_symbols = intel.find_symbol("helper")

    assert len(helper_symbols) == 1
    helper = helper_symbols[0]
    assert helper.file_path == "sample_module.py"
    assert helper.start_line == 1
    assert helper.end_line == 2
