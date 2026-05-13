import subprocess


IGNORE_PATTERNS = [
    ".db",
    ".sqlite",
    ".pyc",
]


def _run(cmd: list[str]) -> list[str]:
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
    modified = _run(["git", "diff", "--name-only"])

    untracked = _run([
        "git",
        "ls-files",
        "--others",
        "--exclude-standard"
    ])

    all_files = modified + untracked

    filtered = []
    seen = set()

    for f in all_files:
        if any(p in f for p in IGNORE_PATTERNS):
            continue

        if f.startswith("context/") or f.startswith("tools/"):
            continue

        if f not in seen:
            seen.add(f)
            filtered.append(f)

    return filtered


def git_diff(file_path: str) -> str:
    result = subprocess.run(
        ["git", "diff", file_path],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout