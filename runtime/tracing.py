from __future__ import annotations
import os
from langfuse import Langfuse
from .state import RuntimeContext
from typing import Any, Dict

def get_langfuse_client():
    """Initializes and returns the Langfuse client."""
    return Langfuse(
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        host=os.environ.get("LANGFUSE_HOST")
    )

def create_langfuse_trace(job_data: Dict[str, Any], context: RuntimeContext):
    """Creates a new trace in Langfuse for a job."""
    langfuse_client = get_langfuse_client()
    return langfuse_client.trace(
        name="refactor_workflow",
        user_id="user-placeholder",
        session_id=context.run_id,
        metadata=job_data
    )
