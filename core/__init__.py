# This __init__.py file serves as the main entry point for the core module of the repo_intel package,

from .models import REGISTERED_MODELS, ModelSpec, get_registered_models
from .router import resolve_model_name
