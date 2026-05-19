from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class RuntimeTask(ABC):
    """Base interface for task-specific runtime behavior."""

    task_type: str = "base"

    @abstractmethod
    def normalize_context(self, optional_context: Optional[str]) -> str:
        """Normalize raw job context into a prompt-ready string."""

    @abstractmethod
    def build_generation_prompt(self, code: str, language: str, context: str) -> str:
        """Build the generation prompt for this task."""

    @abstractmethod
    def build_review_prompt(
        self,
        original_code: str,
        generated_code: str,
        language: str,
        context: str,
    ) -> str:
        """Build the review prompt for this task."""

    @abstractmethod
    def extract_generated_code(self, response: str, language: str) -> str:
        """Extract the task output from the model response."""

    @abstractmethod
    def verify_generated_code(self, generated_code: str, language: str) -> Dict[str, Any]:
        """Run task-specific verification on the generated output."""

    @abstractmethod
    def parse_review_response(self, response: str) -> Dict[str, Any]:
        """Convert a model review into structured approval data."""