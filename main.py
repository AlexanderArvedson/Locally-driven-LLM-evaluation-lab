from repo_intel.core import RepoIntel
from context.builder import ContextBuilder


def main():

    repo = RepoIntel(
        repo_path=".",
        db_path="data/sqlite/repo.db"
    )

    builder = ContextBuilder(repo)

    context = builder.build("generate_user_report")

    print(context)


if __name__ == "__main__":
    main()