# This file contains the RetrievalAPI class, which provides a high-level interface for querying the RepositoryIndex to find symbols by name,
from __future__ import annotations

from repo_intel.core import Symbol
from repo_intel.index import RepositoryIndex

# The RetrievalAPI class provides a high-level interface for querying the RepositoryIndex to find symbols by name.
class RetrievalAPI:
    def __init__(self, repository_index: RepositoryIndex):
        self.repository_index = repository_index

    def find_symbol(self, name: str) -> list[Symbol]:
        return self.repository_index.find_symbol(name)
