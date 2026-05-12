# tools/git.py

import subprocess


def _run_git_command(cmd: list[str]) -> list[str]:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def git_changed_files() -> list[str]:
    """
    Returns both:
    - modified tracked files
    - untracked files

    Excludes ignored files automatically.
    """

    modified_files = _run_git_command(
        ["git", "diff", "--name-only"]
    )

    untracked_files = _run_git_command(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard"
        ]
    )

    # Deduplicate while preserving order
    seen = set()
    combined = []

    for file in modified_files + untracked_files:
        if file not in seen:
            seen.add(file)
            combined.append(file)

    return combined


def git_diff(file_path: str) -> str:
    """
    Returns git diff output for a specific file.
    """

    cmd = ["git", "diff", file_path]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout