# This file defines the router logic for selecting which model to use for a given request.
from __future__ import annotations

from .models import REGISTERED_MODELS

# finds and returns the model name to use based on the preferred model and index. 
# If the preferred model is not available, it falls back to a round-robin selection 
# from the registered models.
def resolve_model_name(preferred: str | None = None, index: int = 0) -> str:
    if preferred and preferred in REGISTERED_MODELS:
        return preferred
    if not REGISTERED_MODELS:
        raise ValueError("No registered models are available")
    return REGISTERED_MODELS[index % len(REGISTERED_MODELS)]
