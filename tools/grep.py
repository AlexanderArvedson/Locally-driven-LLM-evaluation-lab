import subprocess


def grep(query: str, path: str = ".") -> list[dict]:
    """
    Scoped ripgrep search.
    Intended ONLY as fallback signal when structured retrieval fails.
    """

    cmd = [
        "rg",
        query,
        path,
        "--line-number",
        "--no-heading",
        "--type",
        "py",
        "--glob", "!context/**",
        "--glob", "!tools/**",
        "--glob", "!evaluation_suite/**",
        "--glob", "!data/sqlite/**",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip())

    matches = []

    for line in result.stdout.splitlines():
        try:
            file, line_no, text = line.split(":", 2)
            matches.append({
                "file": file,
                "line": int(line_no),
                "text": text.strip()
            })
        except ValueError:
            continue

    return matches