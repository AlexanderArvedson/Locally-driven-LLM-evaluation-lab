from __future__ import annotations

from typing import Dict, Type

from .base import RuntimeTask
from .documentation import DocumentationTask
from .refactoring import RefactoringTask

TASK_REGISTRY: Dict[str, Type[RuntimeTask]] = {
    RefactoringTask.task_type: RefactoringTask,
    DocumentationTask.task_type: DocumentationTask,
}


def create_task(task_type: str = "refactoring") -> RuntimeTask:
    task_class = TASK_REGISTRY.get(task_type)
    if task_class is None:
        available = ", ".join(sorted(TASK_REGISTRY))
        raise ValueError(f"Unknown task type: {task_type}. Available task types: {available}")
    return task_class()
