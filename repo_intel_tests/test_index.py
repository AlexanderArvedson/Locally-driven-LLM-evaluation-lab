from pathlib import Path

from repo_intel.core import RepoIntel


def test_repository_index_rebuild_is_deterministic(tmp_path: Path):
    repo_root = Path("/home/alexa/projects/examensarbete/Locally-driven-LLM/data/repos/basic_python_repo")
    db_path = tmp_path / "index.sqlite"

    intel = RepoIntel(repo_root, db_path)
    first_snapshot = intel.rebuild()
    first_result = intel.find_symbol("helper")

    second_snapshot = intel.rebuild()
    second_result = intel.find_symbol("helper")

    assert first_snapshot.files == second_snapshot.files
    assert first_snapshot.symbols == second_snapshot.symbols
    assert first_result == second_result
    assert db_path.exists()
