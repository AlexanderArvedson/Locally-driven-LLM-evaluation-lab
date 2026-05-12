# This file defines the core configuration for the application, 
# including the model endpoint and repository root path.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# The CoreConfig dataclass holds the configuration for the application,
# including the model endpoint and repository root path.
@dataclass(frozen=True)
class CoreConfig:
    model_endpoint: str = "http://localhost:11434/api/generate"
    repo_root: Path = Path(".")
