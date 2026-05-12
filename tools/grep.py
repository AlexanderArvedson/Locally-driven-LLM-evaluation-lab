# tools/grep.py
import subprocess
from pathlib import Path

def grep(query: str, path: str = ".") -> list[dict]:
    """
    Simple ripgrep wrapper.
    Returns structured matches instead of raw text.
    """

    cmd = [
    "rg",
    query,
    path,
    "--line-number",
    "--no-heading",
    "--type",
    "py"
]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    matches = []

    for line in result.stdout.splitlines():
        # format: file:line:text
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