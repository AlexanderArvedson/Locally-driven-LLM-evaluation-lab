
from __future__ import annotations

from typing import TypedDict, Optional, Dict, Any
import uuid
from dataclasses import dataclass, field
from datetime import datetime


class JobInput(TypedDict):
    """
    Represents the input to a refactoring job.
    """
    prompt: str
    code_to_refactor: str
    language: str
    optional_context: Optional[str]


@dataclass
class RuntimeContext:
    """
    Represents the infrastructure-level context for a run.
    This is kept separate from the GraphState.
    """
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: Optional[str] = None
    job_id: Optional[str] = None
    task_type: Optional[str] = None
    language: Optional[str] = None
    current_model: Optional[str] = None
    start_time: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class GraphState(TypedDict):
    """
    Represents the state of the refactoring workflow graph.

    Attributes:
        initial_prompt: The initial prompt that starts the refactoring process.
        code_to_refactor: The original code that needs to be refactored.
        language: Programming language of the code.
        optional_context: Optional context for refactoring.
        context: The retrieved/processed context for the refactoring task.
        generation: The generated refactored code from the generation node.
        verification: Structured verification output from the verification node.
        review: Structured review feedback from the review node.
        iteration: The current iteration number.
        max_iterations: The maximum number of iterations allowed.
        stop_reason: The reason for stopping the execution.
    """
    initial_prompt: str
    code_to_refactor: str
    language: str
    optional_context: Optional[str]
    context: Optional[str]
    generation: Optional[str]
    verification: Optional[Dict[str, Any]]
    review: Optional[Dict[str, Any]]
    iteration: int
    max_iterations: int
    stop_reason: Optional[str]
