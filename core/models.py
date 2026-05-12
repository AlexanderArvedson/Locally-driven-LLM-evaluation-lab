# This module defines the core data structures and functions related to model specifications for the repo_intel package.
from __future__ import annotations

from dataclasses import dataclass

# The REGISTERED_MODELS list contains the names of the models that are registered 
# and available for use in the application.
REGISTERED_MODELS = [
    "qwen2.5-coder",
    "llama3",
    "mistral",
]

# The ModelSpec dataclass represents the specification of a model, including its name and endpoint.
@dataclass(frozen=True)
class ModelSpec:
    name: str
    endpoint: str = "http://localhost:11434/api/generate"

# The get_registered_models function returns a list of the names of the registered models.
def get_registered_models() -> list[str]:
    return list(REGISTERED_MODELS)
