from repo_intel.core import RepoIntel
from tools.grep import grep
from tools.git import git_changed_files

class ContextBuilder:

    def __init__(self, repo: RepoIntel):
        self.repo = repo

    
    def build(self, task: str) -> str:

        context_parts = []

        # task
        context_parts.append(f"TASK:\n{task}\n")

        # structured retrieval
        symbols = self.repo.find_symbol(task)

        if symbols:
            context_parts.append("RELEVANT SYMBOLS:\n")

            for symbol in symbols:
                context_parts.append(
                    f"- {symbol.name} "
                    f"({symbol.file_path}:{symbol.start_line})"
                )
        
        # grep fallback

        grep_results = grep("task")

        if grep_results:
            context_parts.append("\nGREP MATCHES:\n")

            for match in grep_results[:5]:
                context_parts.append(
                    f"- {match['file']}:{match['line']} "
                    f"{match['text']}"
                )

        # Git awareness
        changed_files = git_changed_files()

        if changed_files:
            context_parts.append("\nCHANGED FILES:\n")

            for file in changed_files:
                context_parts.append(f"- {file}")

        return "\n".join(context_parts)