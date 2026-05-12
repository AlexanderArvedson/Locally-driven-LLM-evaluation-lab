# tools/git.py
import subprocess

def git_changed_files() -> list[str]:
    cmd = ["git", "diff", "--name-only"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    return [
        f.strip()
        for f in result.stdout.splitlines()
        if f.strip()
    ]


def git_diff(file_path: str) -> str:
    cmd = ["git", "diff", file_path]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    return result.stdout