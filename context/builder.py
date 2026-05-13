from repo_intel.core import RepoIntel
from tools.grep import grep
from tools.git import git_changed_files


class ContextBuilder:

    def __init__(self, repo: RepoIntel):
        self.repo = repo

    def build(self, query: str) -> str:

        context = []

        context.append(f"TASK:\n{query}\n")

        # -----------------------
        # 1. REPO INTEL (PRIMARY)
        # -----------------------
        symbols = self.repo.find_symbol(query)

        if symbols:
            context.append("REPO INTEL MATCHES:\n")

            seen = set()

            for s in symbols:
                key = (s.name, s.file_path)

                if key in seen:
                    continue

                seen.add(key)

                context.append(
                    f"- {s.name} ({s.file_path}:{s.start_line})"
                )

        # -----------------------
        # 2. GIT (SECONDARY CONTEXT)
        # -----------------------
        changed_files = git_changed_files()

        if changed_files:
            context.append("\nCHANGED FILES:\n")

            for f in changed_files:
                context.append(f"- {f}")

        # -----------------------
        # 3. GREP (STRICT FALLBACK ONLY)
        # -----------------------
        # IMPORTANT: no query expansion anymore
        grep_results = grep(query)

        if grep_results:
            context.append("\nGREP MATCHES (fallback):\n")

            seen_files = set()

            for m in grep_results:
                if m["file"] in seen_files:
                    continue

                seen_files.add(m["file"])

                context.append(
                    f"- {m['file']}:{m['line']} {m['text']}"
                )

                if len(seen_files) >= 3:
                    break

        return "\n".join(context)