
from __future__ import annotations

from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage
import uuid
from dataclasses import dataclass, field

@dataclass
class RuntimeContext:
    """
    Represents the infrastructure-level context for a run.
    This is kept separate from the GraphState.
    """
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: Optional[str] = None
    job_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        initial_prompt: The initial prompt that starts the refactoring process.
        code_to_refactor: The code that needs to be refactored.
        context: The retrieved context for the refactoring task.
        generation: The generated code from the refactor agent.
        review: The review feedback from the reviewer agent.
        validation_result: The result of the code validation.
        iteration: The current iteration number.
        max_iterations: The maximum number of iterations allowed.
        stop_reason: The reason for stopping the execution.
    """
    initial_prompt: str
    code_to_refactor: str
    context: Optional[str]
    generation: Optional[str]
    review: Optional[str]
    validation_result: Optional[str]
    iteration: int
    max_iterations: int
    stop_reason: Optional[str]
