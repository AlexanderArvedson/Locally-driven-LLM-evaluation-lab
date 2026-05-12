from pathlib import Path

from repo_intel.scanner import scan_repository


def test_scan_repository_ignores_venv_and_detects_tests(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".gitignore").write_text("build/\n", encoding="utf-8")
    (repo_root / "module.py").write_text("def x():\n    return 1\n", encoding="utf-8")
    (repo_root / ".venv").mkdir()
    (repo_root / ".venv" / "ignored.py").write_text("def y():\n    return 2\n", encoding="utf-8")
    (repo_root / "tests").mkdir()
    (repo_root / "tests" / "test_module.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")

    files = scan_repository(repo_root)

    assert [file.path for file in files] == ["module.py", "tests/test_module.py"]
    assert files[0].language == "python"
    assert files[0].is_test is False
    assert files[1].is_test is True
